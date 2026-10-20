import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token, session_key
from app.core.token_store import get_session_version, is_jti_revoked
from app.db.session import get_db
from app.models.enums import MarketplaceSupplierStatus, PlatformStaffRole, SupplierMembershipRole, SupplierMembershipStatus, UserRole
from app.models.marketplace_supplier import MarketplaceSupplier
from app.models.platform_admin import PlatformAdmin
from app.models.supplier_user import SupplierMembership, SupplierUser
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def _check_session_live(payload: dict, token_type: str, subject: str) -> None:
    """Phase 9.1: rejects a token whose jti was explicitly revoked (single-
    session logout, or a rotated-away refresh token being replayed), or
    whose "sv" claim is behind the subject's current session version
    (logout-all, suspension, deactivation, password change). Raises the same
    401 every other invalid-token path raises, so a revoked token is
    indistinguishable from an expired or malformed one to the caller."""
    jti = payload.get("jti")
    if jti and is_jti_revoked(jti):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("sv", 0) < get_session_version(session_key(token_type, subject)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")


@dataclass
class SupplierSession:
    """The authenticated identity for every /supplier-portal route: who is
    logged in, and which single marketplace supplier they're currently
    acting for (never more than one at a time, per PLAT-038's explicit
    active-supplier-selection requirement)."""

    user: SupplierUser
    membership: SupplierMembership
    marketplace_supplier_id: uuid.UUID


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    _check_session_live(payload, "access", payload.get("sub", ""))

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or not user.company.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    return user


def get_current_platform_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> PlatformAdmin:
    # Deliberately separate from get_current_user: a tenant "access" token must never
    # work here, and a "platform_access" token must never work on tenant endpoints.
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "platform_access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    _check_session_live(payload, "platform_access", payload.get("sub", ""))

    try:
        admin_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    return admin


def get_current_supplier_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> SupplierSession:
    # Same separation as the other two: a "supplier_access" token is its own
    # type claim, so a tenant or platform token can never satisfy this, and
    # vice versa -- this route family can never be reached from either of
    # the other two token types.
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "supplier_access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    _check_session_live(payload, "supplier_access", payload.get("sub", ""))

    try:
        supplier_user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    active_supplier_id = payload.get("active_supplier_id")
    if not active_supplier_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Select a supplier organization before continuing")
    try:
        active_supplier_id = uuid.UUID(active_supplier_id)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    user = db.query(SupplierUser).filter(SupplierUser.id == supplier_user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    membership = (
        db.query(SupplierMembership)
        .filter(SupplierMembership.supplier_user_id == user.id, SupplierMembership.marketplace_supplier_id == active_supplier_id)
        .first()
    )
    if not membership or membership.status != SupplierMembershipStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You're no longer authorized for this supplier organization")

    supplier = db.query(MarketplaceSupplier).filter(MarketplaceSupplier.id == active_supplier_id).first()
    if not supplier or supplier.verification_status != MarketplaceSupplierStatus.VERIFIED:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This supplier organization isn't currently verified")

    return SupplierSession(user=user, membership=membership, marketplace_supplier_id=active_supplier_id)


def require_supplier_roles(*allowed_roles: SupplierMembershipRole) -> Callable[[SupplierSession], SupplierSession]:
    def _check(session: SupplierSession = Depends(get_current_supplier_user)) -> SupplierSession:
        if session.membership.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return session

    return _check


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return _check


def require_platform_roles(*allowed_roles: PlatformStaffRole) -> Callable[[PlatformAdmin], PlatformAdmin]:
    def _check(admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
        if admin.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return admin

    return _check
