"""Supplier user invitations (PLAT-038) -- mirrors user_service.py's tenant
invitation mechanics byte-for-byte (secrets.token_urlsafe(32) + SHA-256
token_hash, 7-day expiry). A SupplierUser is only ever created by accepting
one of these; there is no open self-registration, and every invitation must
name a real, already-approved marketplace supplier -- never creates one."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.enums import MarketplaceSupplierStatus, SupplierMembershipStatus
from app.models.marketplace_supplier import MarketplaceSupplier
from app.models.platform_admin import PlatformAdmin
from app.models.supplier_user import SupplierInvitation, SupplierMembership, SupplierUser
from app.schemas.supplier_portal import SupplierAcceptInvitation, SupplierInvitationCreate, SupplierInvitationCreated, SupplierInvitationInfo, SupplierInvitationRead
from app.services import email_service

INVITE_VALID_FOR = timedelta(days=7)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _read(invitation: SupplierInvitation, inviter_name: str | None) -> SupplierInvitationRead:
    return SupplierInvitationRead(
        id=invitation.id, email=invitation.email, full_name=invitation.full_name, role=invitation.role,
        invited_by_name=inviter_name, created_at=invitation.created_at, expires_at=invitation.expires_at,
        expired=_aware(invitation.expires_at) <= _now(),
    )


def _open_invitations(db: Session, marketplace_supplier_id: uuid.UUID):
    return db.query(SupplierInvitation).filter(
        SupplierInvitation.marketplace_supplier_id == marketplace_supplier_id,
        SupplierInvitation.accepted_at.is_(None),
        SupplierInvitation.revoked_at.is_(None),
    )


def _get_verified_supplier(db: Session, marketplace_supplier_id: uuid.UUID) -> MarketplaceSupplier:
    supplier = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id == marketplace_supplier_id).first()
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Marketplace supplier not found")
    if supplier.verification_status != MarketplaceSupplierStatus.VERIFIED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a verified marketplace supplier can have portal users")
    return supplier


def create_invitation_by_staff(db: Session, actor: PlatformAdmin, marketplace_supplier_id: uuid.UUID, payload: SupplierInvitationCreate) -> SupplierInvitationCreated:
    return _create(db, marketplace_supplier_id, payload, invited_by_staff_id=actor.id, inviter_name=actor.full_name)


def create_invitation_by_supplier(db: Session, marketplace_supplier_id: uuid.UUID, inviter_supplier_user_id: uuid.UUID, inviter_name: str, payload: SupplierInvitationCreate) -> SupplierInvitationCreated:
    return _create(db, marketplace_supplier_id, payload, invited_by_supplier_user_id=inviter_supplier_user_id, inviter_name=inviter_name)


def _create(
    db: Session,
    marketplace_supplier_id: uuid.UUID,
    payload: SupplierInvitationCreate,
    inviter_name: str,
    invited_by_staff_id: uuid.UUID | None = None,
    invited_by_supplier_user_id: uuid.UUID | None = None,
) -> SupplierInvitationCreated:
    _get_verified_supplier(db, marketplace_supplier_id)
    email = payload.email.strip().lower()
    # An existing SupplierUser is fine -- a person can hold memberships in
    # several suppliers (PLAT-038). Only a membership already covering THIS
    # supplier is a real conflict.
    existing_user = db.query(SupplierUser).filter(func.lower(SupplierUser.email) == email).first()
    if existing_user:
        already_member = (
            db.query(SupplierMembership)
            .filter(SupplierMembership.supplier_user_id == existing_user.id, SupplierMembership.marketplace_supplier_id == marketplace_supplier_id)
            .first()
        )
        if already_member:
            raise HTTPException(status.HTTP_409_CONFLICT, "This person is already a member of this supplier organization")

    for old in _open_invitations(db, marketplace_supplier_id).filter(func.lower(SupplierInvitation.email) == email):
        old.revoked_at = _now()

    token = secrets.token_urlsafe(32)
    invitation = SupplierInvitation(
        marketplace_supplier_id=marketplace_supplier_id,
        email=email,
        full_name=payload.full_name.strip() if payload.full_name else None,
        role=payload.role,
        token_hash=_hash_token(token),
        expires_at=_now() + INVITE_VALID_FOR,
        invited_by_staff_id=invited_by_staff_id,
        invited_by_supplier_user_id=invited_by_supplier_user_id,
    )
    db.add(invitation)
    db.flush()
    db.commit()
    db.refresh(invitation)
    supplier = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id == marketplace_supplier_id).first()
    email_service.send_templated(
        db, "account_invitation", email,
        {
            "org_name": supplier.name if supplier else "a supplier organization", "inviter_name": inviter_name or "A team member", "role": payload.role.value,
            "accept_url": f"{get_settings().app_base_url}/supplier-portal/accept-invite?token={token}", "expires_at": invitation.expires_at.isoformat(),
        },
        dedup_key=f"supplier-invitation:{invitation.id}",
    )
    return SupplierInvitationCreated(**_read(invitation, inviter_name).model_dump(), token=token)


def list_invitations(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupplierInvitationRead]:
    rows = (
        _open_invitations(db, marketplace_supplier_id)
        .outerjoin(PlatformAdmin, PlatformAdmin.id == SupplierInvitation.invited_by_staff_id)
        .outerjoin(SupplierUser, SupplierUser.id == SupplierInvitation.invited_by_supplier_user_id)
        .with_entities(SupplierInvitation, PlatformAdmin.full_name, SupplierUser.full_name)
        .order_by(SupplierInvitation.created_at.desc())
        .all()
    )
    return [_read(invitation, staff_name or user_name) for invitation, staff_name, user_name in rows]


def revoke_invitation(db: Session, marketplace_supplier_id: uuid.UUID, invitation_id: uuid.UUID) -> None:
    invitation = _open_invitations(db, marketplace_supplier_id).filter(SupplierInvitation.id == invitation_id).first()
    if not invitation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")
    invitation.revoked_at = _now()
    db.commit()


def _usable_invitation(db: Session, token: str) -> SupplierInvitation:
    invitation = db.query(SupplierInvitation).filter(SupplierInvitation.token_hash == _hash_token(token)).first()
    if not invitation or invitation.accepted_at or invitation.revoked_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This invitation link isn't valid. Ask for a new one.")
    if _aware(invitation.expires_at) <= _now():
        raise HTTPException(status.HTTP_410_GONE, "This invitation has expired. Ask for a new one.")
    return invitation


def get_invitation_info(db: Session, token: str) -> SupplierInvitationInfo:
    invitation = _usable_invitation(db, token)
    supplier = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id == invitation.marketplace_supplier_id).first()
    return SupplierInvitationInfo(
        marketplace_supplier_name=supplier.name, email=invitation.email, full_name=invitation.full_name, role=invitation.role
    )


def accept_invitation(db: Session, payload: SupplierAcceptInvitation) -> SupplierUser:
    invitation = _usable_invitation(db, payload.token)
    existing = db.query(SupplierUser).filter(func.lower(SupplierUser.email) == invitation.email.lower()).first()
    if existing:
        user = existing  # a second invitation (e.g. to another supplier) for an existing portal account
    else:
        user = SupplierUser(email=invitation.email, hashed_password=hash_password(payload.password), full_name=payload.full_name.strip())
        db.add(user)
        db.flush()

    membership = (
        db.query(SupplierMembership)
        .filter(SupplierMembership.supplier_user_id == user.id, SupplierMembership.marketplace_supplier_id == invitation.marketplace_supplier_id)
        .first()
    )
    if membership:
        membership.status = SupplierMembershipStatus.ACTIVE
        membership.role = invitation.role
        membership.revoked_at = None
        membership.suspended_at = None
    else:
        db.add(SupplierMembership(supplier_user_id=user.id, marketplace_supplier_id=invitation.marketplace_supplier_id, role=invitation.role))

    invitation.accepted_at = _now()
    db.commit()
    db.refresh(user)
    return user
