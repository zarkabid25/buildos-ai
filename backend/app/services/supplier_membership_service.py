"""Supplier membership management (PLAT-038): listing a supplier's own team,
suspending/revoking/reinstating a member, and changing a member's role.
Suspension and revocation are status changes, never deletions -- the
membership row (and the fact someone was once authorized) is never erased."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import SupplierMembershipRole, SupplierMembershipStatus
from app.models.supplier_user import SupplierMembership, SupplierUser
from app.schemas.supplier_portal import SupplierMembershipRead


def _read(m: SupplierMembership, user: SupplierUser) -> SupplierMembershipRead:
    return SupplierMembershipRead(id=m.id, supplier_user_id=m.supplier_user_id, user_full_name=user.full_name, user_email=user.email, role=m.role, status=m.status, created_at=m.created_at)


def list_members(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupplierMembershipRead]:
    rows = (
        db.query(SupplierMembership, SupplierUser)
        .join(SupplierUser, SupplierUser.id == SupplierMembership.supplier_user_id)
        .filter(SupplierMembership.marketplace_supplier_id == marketplace_supplier_id)
        .order_by(SupplierMembership.created_at.asc())
        .all()
    )
    return [_read(m, u) for m, u in rows]


def _get(db: Session, marketplace_supplier_id: uuid.UUID, membership_id: uuid.UUID) -> SupplierMembership:
    membership = db.query(SupplierMembership).filter(SupplierMembership.marketplace_supplier_id == marketplace_supplier_id, SupplierMembership.id == membership_id).first()
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membership not found")
    return membership


def suspend_member(db: Session, marketplace_supplier_id: uuid.UUID, membership_id: uuid.UUID, actor_membership_id: uuid.UUID) -> SupplierMembershipRead:
    if membership_id == actor_membership_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't suspend your own membership")
    from datetime import datetime, timezone

    membership = _get(db, marketplace_supplier_id, membership_id)
    membership.status = SupplierMembershipStatus.SUSPENDED
    membership.suspended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(membership)
    user = db.query(SupplierUser).filter(SupplierUser.id == membership.supplier_user_id).first()
    return _read(membership, user)


def revoke_member(db: Session, marketplace_supplier_id: uuid.UUID, membership_id: uuid.UUID, actor_membership_id: uuid.UUID) -> SupplierMembershipRead:
    if membership_id == actor_membership_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't revoke your own membership")
    from datetime import datetime, timezone

    membership = _get(db, marketplace_supplier_id, membership_id)
    membership.status = SupplierMembershipStatus.REVOKED
    membership.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(membership)
    user = db.query(SupplierUser).filter(SupplierUser.id == membership.supplier_user_id).first()
    return _read(membership, user)


def reinstate_member(db: Session, marketplace_supplier_id: uuid.UUID, membership_id: uuid.UUID) -> SupplierMembershipRead:
    membership = _get(db, marketplace_supplier_id, membership_id)
    if membership.status == SupplierMembershipStatus.REVOKED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A revoked membership can't be reinstated -- invite them again")
    membership.status = SupplierMembershipStatus.ACTIVE
    membership.suspended_at = None
    db.commit()
    db.refresh(membership)
    user = db.query(SupplierUser).filter(SupplierUser.id == membership.supplier_user_id).first()
    return _read(membership, user)


def change_role(db: Session, marketplace_supplier_id: uuid.UUID, membership_id: uuid.UUID, role: SupplierMembershipRole) -> SupplierMembershipRead:
    membership = _get(db, marketplace_supplier_id, membership_id)
    membership.role = role
    db.commit()
    db.refresh(membership)
    user = db.query(SupplierUser).filter(SupplierUser.id == membership.supplier_user_id).first()
    return _read(membership, user)
