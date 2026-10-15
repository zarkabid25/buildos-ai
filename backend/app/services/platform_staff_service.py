import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import PlatformStaffRole
from app.models.platform_admin import PlatformAdmin
from app.models.platform_invitation import PlatformInvitation
from app.schemas.platform import (
    PlatformAcceptInvitation,
    PlatformAdminRead,
    PlatformInvitationCreate,
    PlatformInvitationCreated,
    PlatformInvitationInfo,
    PlatformInvitationRead,
    PlatformStaffUpdate,
)
from app.services import platform_audit_service

INVITE_VALID_FOR = timedelta(days=7)


def list_staff(db: Session) -> list[PlatformAdminRead]:
    admins = db.query(PlatformAdmin).order_by(PlatformAdmin.full_name.asc()).all()
    return [PlatformAdminRead.model_validate(a) for a in admins]


def update_staff(db: Session, actor: PlatformAdmin, admin_id: uuid.UUID, payload: PlatformStaffUpdate) -> PlatformAdminRead:
    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not admin:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")

    changes = payload.model_dump(exclude_unset=True)
    if admin.id == actor.id and changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't change your own role or status")

    touches_owner = admin.role == PlatformStaffRole.OWNER or changes.get("role") == PlatformStaffRole.OWNER
    if touches_owner and actor.role != PlatformStaffRole.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an owner can manage owners")

    before = {"role": admin.role, "is_active": admin.is_active}
    if "role" in changes and changes["role"] is not None:
        admin.role = changes["role"]
    if "is_active" in changes and changes["is_active"] is not None:
        admin.is_active = changes["is_active"]

    if admin.role != before["role"]:
        platform_audit_service.record(
            db, actor.id, "staff.role_changed", "platform_admin", admin.id,
            f"{admin.full_name}: role {before['role'].value} -> {admin.role.value}",
            {"from": before["role"].value, "to": admin.role.value},
        )
    if admin.is_active != before["is_active"]:
        action = "staff.reactivated" if admin.is_active else "staff.deactivated"
        platform_audit_service.record(
            db, actor.id, action, "platform_admin", admin.id,
            f"{admin.full_name} {'reactivated' if admin.is_active else 'deactivated'}",
        )
    db.commit()
    db.refresh(admin)
    return PlatformAdminRead.model_validate(admin)


# ---- Invitations (PLAT-010) -------------------------------------------------------


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _invitation_read(invitation: PlatformInvitation, inviter_name: str | None) -> PlatformInvitationRead:
    return PlatformInvitationRead(
        id=invitation.id,
        email=invitation.email,
        full_name=invitation.full_name,
        role=invitation.role,
        invited_by_name=inviter_name,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        expired=_aware(invitation.expires_at) <= _now(),
    )


def _open_invitations(db: Session):
    return db.query(PlatformInvitation).filter(
        PlatformInvitation.accepted_at.is_(None), PlatformInvitation.revoked_at.is_(None)
    )


def create_invitation(db: Session, actor: PlatformAdmin, payload: PlatformInvitationCreate) -> PlatformInvitationCreated:
    email = payload.email.strip().lower()
    if payload.role == PlatformStaffRole.OWNER and actor.role != PlatformStaffRole.OWNER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an owner can invite an owner")
    if db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Someone with this email already has a staff account")

    for old in _open_invitations(db).filter(func.lower(PlatformInvitation.email) == email):
        old.revoked_at = _now()

    token = secrets.token_urlsafe(32)
    invitation = PlatformInvitation(
        email=email,
        full_name=payload.full_name.strip() if payload.full_name else None,
        role=payload.role,
        token_hash=_hash_token(token),
        expires_at=_now() + INVITE_VALID_FOR,
        invited_by_id=actor.id,
    )
    db.add(invitation)
    db.flush()
    platform_audit_service.record(
        db, actor.id, "staff.invited", "platform_invitation", invitation.id,
        f"Invited {email} as {payload.role.value}",
    )
    db.commit()
    db.refresh(invitation)
    return PlatformInvitationCreated(**_invitation_read(invitation, actor.full_name).model_dump(), token=token)


def list_invitations(db: Session) -> list[PlatformInvitationRead]:
    rows = (
        _open_invitations(db)
        .outerjoin(PlatformAdmin, PlatformAdmin.id == PlatformInvitation.invited_by_id)
        .with_entities(PlatformInvitation, PlatformAdmin.full_name)
        .order_by(PlatformInvitation.created_at.desc())
        .all()
    )
    return [_invitation_read(invitation, name) for invitation, name in rows]


def revoke_invitation(db: Session, actor: PlatformAdmin, invitation_id: uuid.UUID) -> None:
    invitation = _open_invitations(db).filter(PlatformInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    invitation.revoked_at = _now()
    platform_audit_service.record(
        db, actor.id, "staff.invitation_revoked", "platform_invitation", invitation.id,
        f"Invitation for {invitation.email} revoked",
    )
    db.commit()


def _usable_invitation(db: Session, token: str) -> PlatformInvitation:
    invitation = db.query(PlatformInvitation).filter(PlatformInvitation.token_hash == _hash_token(token)).first()
    if not invitation or invitation.accepted_at or invitation.revoked_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This invitation link isn't valid. Ask for a new one.")
    if _aware(invitation.expires_at) <= _now():
        raise HTTPException(status.HTTP_410_GONE, "This invitation has expired. Ask for a new one.")
    return invitation


def get_invitation_info(db: Session, token: str) -> PlatformInvitationInfo:
    invitation = _usable_invitation(db, token)
    return PlatformInvitationInfo(email=invitation.email, full_name=invitation.full_name, role=invitation.role)


def accept_invitation(db: Session, payload: PlatformAcceptInvitation) -> PlatformAdmin:
    invitation = _usable_invitation(db, payload.token)
    if db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == invitation.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Someone with this email already has a staff account")
    admin = PlatformAdmin(
        email=invitation.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=invitation.role,
    )
    db.add(admin)
    db.flush()
    invitation.accepted_at = _now()
    platform_audit_service.record(
        db, admin.id, "staff.joined", "platform_admin", admin.id,
        f"{admin.full_name} joined as {admin.role.value} (invited)",
    )
    db.commit()
    db.refresh(admin)
    return admin
