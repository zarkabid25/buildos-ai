"""Supplier portal authentication (PLAT-038) -- the third, fully independent
auth system in this app (tenant users, platform staff, now supplier users).
A SupplierUser is only ever created by accepting a SupplierInvitation
(see supplier_invitation_service.py); there is no open self-registration
endpoint, so a supplier account can never exist without first being tied to
a real, already-approved MarketplaceSupplier."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import (
    create_supplier_access_token,
    create_supplier_refresh_token,
    decode_token,
    logout_all_sessions,
    revoke_token,
    rotate_refresh_or_reject,
    verify_password,
)
from app.models.enums import MarketplaceSupplierStatus, SupplierMembershipStatus
from app.models.marketplace_supplier import MarketplaceSupplier
from app.models.supplier_user import SupplierMembership, SupplierUser
from app.schemas.supplier_portal import SupplierAuthResponse, SupplierLoginRequest, SupplierMembershipSummary, SupplierTokenPair, SupplierUserRead


def _active_memberships(db: Session, supplier_user_id: uuid.UUID) -> list[tuple[SupplierMembership, MarketplaceSupplier]]:
    rows = (
        db.query(SupplierMembership, MarketplaceSupplier)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == SupplierMembership.marketplace_supplier_id)
        .filter(
            SupplierMembership.supplier_user_id == supplier_user_id,
            SupplierMembership.status == SupplierMembershipStatus.ACTIVE,
            MarketplaceSupplier.verification_status == MarketplaceSupplierStatus.VERIFIED,
        )
        .all()
    )
    return rows


def _summaries(rows: list[tuple[SupplierMembership, MarketplaceSupplier]]) -> list[SupplierMembershipSummary]:
    return [
        SupplierMembershipSummary(marketplace_supplier_id=supplier.id, marketplace_supplier_name=supplier.name, role=m.role, status=m.status)
        for m, supplier in rows
    ]


def _issue(user: SupplierUser, active_supplier_id: uuid.UUID | None) -> SupplierTokenPair:
    return SupplierTokenPair(
        access_token=create_supplier_access_token(str(user.id), str(active_supplier_id) if active_supplier_id else None),
        refresh_token=create_supplier_refresh_token(str(user.id)),
        active_supplier_id=active_supplier_id,
    )


def login(db: Session, payload: SupplierLoginRequest) -> SupplierAuthResponse:
    user = db.query(SupplierUser).filter(func.lower(SupplierUser.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been deactivated")

    memberships = _active_memberships(db, user.id)
    if not memberships:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You have no active supplier organization membership")

    # Exactly one active membership -> log straight in already "selected".
    # Two or more -> explicit selection is required (PLAT-038), so the token
    # is issued without an active supplier until select_supplier is called.
    active_id = memberships[0][0].marketplace_supplier_id if len(memberships) == 1 else None
    tokens = _issue(user, active_id)
    return SupplierAuthResponse(**tokens.model_dump(), user=SupplierUserRead.model_validate(user), memberships=_summaries(memberships))


def select_supplier(db: Session, refresh_token: str, marketplace_supplier_id: uuid.UUID) -> SupplierTokenPair:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "supplier_refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    # Deliberately NOT rotated here (unlike refresh() below): this is a
    # scoping step on an already-valid session -- a multi-supplier user is
    # expected to call this more than once from the same login (switching
    # which supplier they're acting as), so the original refresh token must
    # stay usable for that, not be single-use.
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.query(SupplierUser).filter(SupplierUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    memberships = {m.marketplace_supplier_id: m for m, _s in _active_memberships(db, user.id)}
    if marketplace_supplier_id not in memberships:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You're not authorized for that supplier organization")

    return _issue(user, marketplace_supplier_id)


def refresh(db: Session, refresh_token: str) -> SupplierTokenPair:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "supplier_refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    rotate_refresh_or_reject(payload, "supplier_refresh")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.query(SupplierUser).filter(SupplierUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    memberships = _active_memberships(db, user.id)
    active_id = memberships[0][0].marketplace_supplier_id if len(memberships) == 1 else None
    return _issue(user, active_id)


def my_memberships(db: Session, supplier_user_id: uuid.UUID) -> list[SupplierMembershipSummary]:
    return _summaries(_active_memberships(db, supplier_user_id))


def logout(access_token_payload: dict) -> None:
    revoke_token(access_token_payload)


def logout_all(supplier_user_id: uuid.UUID) -> None:
    logout_all_sessions("supplier_access", str(supplier_user_id))
