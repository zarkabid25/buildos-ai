import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.token_store import bump_session_version, claim_jti, get_session_version, revoke_jti

settings = get_settings()

_SESSION_PREFIX = {
    "access": "user", "refresh": "user",
    "platform_access": "platform", "platform_refresh": "platform",
    "supplier_access": "supplier", "supplier_refresh": "supplier",
}


def session_key(token_type: str, subject: str) -> str:
    """The key session versions (logout-all, suspension, password change,
    reuse-detection) are tracked under -- shared between a type's access and
    refresh tokens, since invalidating one must invalidate both."""
    return f"{_SESSION_PREFIX[token_type]}:{subject}"

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
        # Phase 9.1 (Task 1): the subject's session version *at issue time*.
        # Bumping it (logout-all, suspension, password change, reuse
        # detection) immediately invalidates this and every other
        # already-issued token for the same subject -- see deps.py.
        "sv": get_session_version(session_key(token_type, subject)),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm=settings.jwt_algorithm)


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
        return jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def rotate_refresh_or_reject(payload: dict[str, Any], token_type: str) -> None:
    """Phase 9.1 (Task 1; made race-safe in Phase 10): called by every
    refresh() service right after decoding a presented refresh token.
    Enforces single-use rotation via `claim_jti`'s atomic SET-if-not-exists
    -- a refresh token that's already been claimed once means either normal
    re-use of an old browser tab/stale client, or a stolen token being
    replayed -- either way it's treated as a reuse attack and the ENTIRE
    session is revoked (every token for this subject, not just this one),
    matching standard refresh-rotation guidance. The old implementation
    checked "is it revoked?" and then separately called "revoke it" as two
    steps, which left a race window for two concurrent requests with the
    same refresh token to both pass the check; `claim_jti` closes that by
    doing both atomically in Redis (or under a single lock in-process)."""
    subject = payload.get("sub", "")
    key = session_key(token_type, subject)
    jti = payload.get("jti")
    if payload.get("sv", 0) < get_session_version(key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    if jti and not claim_jti(jti, max(1.0, payload.get("exp", 0) - time.time())):
        bump_session_version(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")


def revoke_token(payload: dict[str, Any]) -> None:
    """Logout of exactly the session this one token belongs to."""
    jti = payload.get("jti")
    if jti:
        revoke_jti(jti, max(1.0, payload.get("exp", 0) - time.time()))


def logout_all_sessions(token_type: str, subject: str) -> None:
    """Logout-all-sessions, and the same primitive used for suspension,
    deactivation, and password changes."""
    bump_session_version(session_key(token_type, subject))
