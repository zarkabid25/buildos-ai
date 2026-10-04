import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.company import Company
from app.models.invitation import Invitation
from app.models.user import User
from app.schemas.user import (
    AcceptInvitation,
    InvitationCreate,
    InvitationCreated,
    InvitationInfo,
    InvitationRead,
    PasswordChange,
    UserAdminUpdate,
    UserSelfUpdate,
)
from app.services import audit_service


def update_me(db: Session, user: User, payload: UserSelfUpdate) -> User:
    user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: PasswordChange) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()


def list_users(db: Session, company_id: uuid.UUID) -> list[User]:
    return db.query(User).filter(User.company_id == company_id).order_by(User.full_name.asc()).all()


def update_user(db: Session, actor: User, user_id: uuid.UUID, payload: UserAdminUpdate) -> User:
    user = db.query(User).filter(User.company_id == actor.company_id, User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes = payload.model_dump(exclude_unset=True)
    # An admin changing their own role or deactivating themselves could leave the
    # company with nobody able to manage it.
    if user.id == actor.id and changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't change your own role or status")
    # Only a super admin may create or modify another super admin.
    touches_super = user.role == UserRole.SUPER_ADMIN or changes.get("role") == UserRole.SUPER_ADMIN
    if touches_super and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a super admin can manage super admins")

    before = {"role": user.role, "is_active": user.is_active}
    apply_changes(user, changes)
    if "role" in changes and changes["role"] != before["role"]:
        audit_service.record(
            db, actor.company_id, actor.id, "user.role_changed", "user", user.id,
            f"{user.full_name}: role {before['role'].value} -> {user.role.value}",
            {"from": before["role"].value, "to": user.role.value},
        )
    if "is_active" in changes and changes["is_active"] != before["is_active"]:
        action = "user.reactivated" if user.is_active else "user.deactivated"
        audit_service.record(
            db, actor.company_id, actor.id, action, "user", user.id,
            f"{user.full_name} {'reactivated' if user.is_active else 'deactivated'}",
        )
    db.commit()
    db.refresh(user)
    return user


# ---- Invitations (BUILD-105) -----------------------------------------------------

INVITE_VALID_FOR = timedelta(days=7)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    # SQLite hands back naive datetimes; they were stored as UTC.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _invitation_read(invitation: Invitation, inviter_name: str | None) -> InvitationRead:
    return InvitationRead(
        id=invitation.id,
        email=invitation.email,
        full_name=invitation.full_name,
        role=invitation.role,
        invited_by_name=inviter_name,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        expired=_aware(invitation.expires_at) <= _now(),
    )


def _open_invitations(db: Session, company_id: uuid.UUID):
    return db.query(Invitation).filter(
        Invitation.company_id == company_id, Invitation.accepted_at.is_(None), Invitation.revoked_at.is_(None)
    )


def create_invitation(db: Session, actor: User, payload: InvitationCreate) -> InvitationCreated:
    email = payload.email.strip().lower()
    if payload.role == UserRole.SUPER_ADMIN and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a super admin can invite a super admin")
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Someone with this email already has an account")

    # Inviting the same person again replaces the earlier link.
    for old in _open_invitations(db, actor.company_id).filter(func.lower(Invitation.email) == email):
        old.revoked_at = _now()

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        company_id=actor.company_id,
        email=email,
        full_name=payload.full_name.strip() if payload.full_name else None,
        role=payload.role,
        token_hash=_hash_token(token),
        expires_at=_now() + INVITE_VALID_FOR,
        invited_by_id=actor.id,
    )
    db.add(invitation)
    db.flush()
    audit_service.record(
        db, actor.company_id, actor.id, "user.invited", "invitation", invitation.id,
        f"Invited {email} as {payload.role.value}",
    )
    db.commit()
    db.refresh(invitation)
    return InvitationCreated(**_invitation_read(invitation, actor.full_name).model_dump(), token=token)


def list_invitations(db: Session, company_id: uuid.UUID) -> list[InvitationRead]:
    rows = (
        _open_invitations(db, company_id)
        .outerjoin(User, User.id == Invitation.invited_by_id)
        .with_entities(Invitation, User.full_name)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    return [_invitation_read(invitation, name) for invitation, name in rows]


def revoke_invitation(db: Session, actor: User, invitation_id: uuid.UUID) -> None:
    invitation = _open_invitations(db, actor.company_id).filter(Invitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    invitation.revoked_at = _now()
    audit_service.record(
        db, actor.company_id, actor.id, "user.invitation_revoked", "invitation", invitation.id,
        f"Invitation for {invitation.email} revoked",
    )
    db.commit()


def _usable_invitation(db: Session, token: str) -> Invitation:
    invitation = db.query(Invitation).filter(Invitation.token_hash == _hash_token(token)).first()
    if not invitation or invitation.accepted_at or invitation.revoked_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This invitation link isn't valid. Ask for a new one.")
    if _aware(invitation.expires_at) <= _now():
        raise HTTPException(status.HTTP_410_GONE, "This invitation has expired. Ask for a new one.")
    return invitation


def get_invitation_info(db: Session, token: str) -> InvitationInfo:
    invitation = _usable_invitation(db, token)
    company = db.get(Company, invitation.company_id)
    return InvitationInfo(
        company_name=company.name, email=invitation.email, full_name=invitation.full_name, role=invitation.role
    )


def accept_invitation(db: Session, payload: AcceptInvitation) -> User:
    invitation = _usable_invitation(db, payload.token)
    if db.query(User).filter(func.lower(User.email) == invitation.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Someone with this email already has an account")
    user = User(
        company_id=invitation.company_id,
        email=invitation.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=invitation.role,
    )
    db.add(user)
    db.flush()
    invitation.accepted_at = _now()
    audit_service.record(
        db, invitation.company_id, user.id, "user.joined", "user", user.id,
        f"{user.full_name} joined as {user.role.value} (invited)",
    )
    db.commit()
    db.refresh(user)
    return user
