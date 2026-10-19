import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# passlib's CryptContext is unmaintained and breaks against bcrypt>=4.1 (it probes
# a private `__about__` attribute bcrypt no longer exposes), so we call bcrypt directly.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))


def _create_token(
    subject: str,
    expires_delta: timedelta,
    token_type: Literal["access", "refresh", "platform_access", "platform_refresh", "supplier_access", "supplier_refresh"],
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: str) -> str:
    return _create_token(
        user_id, timedelta(minutes=settings.access_token_expire_minutes), "access"
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        user_id, timedelta(days=settings.refresh_token_expire_days), "refresh"
    )


def create_platform_access_token(admin_id: str) -> str:
    return _create_token(
        admin_id, timedelta(minutes=settings.access_token_expire_minutes), "platform_access"
    )


def create_platform_refresh_token(admin_id: str) -> str:
    return _create_token(
        admin_id, timedelta(days=settings.refresh_token_expire_days), "platform_refresh"
    )


def create_supplier_access_token(supplier_user_id: str, active_supplier_id: str | None) -> str:
    """`active_supplier_id` is the currently-selected marketplace supplier
    (PLAT-038's "explicit active-supplier selection") -- null when a
    multi-membership user has just logged in but not yet picked one, in
    which case every supplier-scoped endpoint refuses the token (see
    get_current_supplier_user) until select_supplier mints a new one."""
    return _create_token(
        supplier_user_id, timedelta(minutes=settings.access_token_expire_minutes), "supplier_access",
        extra_claims={"active_supplier_id": active_supplier_id},
    )


def create_supplier_refresh_token(supplier_user_id: str) -> str:
    return _create_token(
        supplier_user_id, timedelta(days=settings.refresh_token_expire_days), "supplier_refresh"
    )


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
