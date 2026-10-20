import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    logout_all_sessions,
    revoke_token,
    rotate_refresh_or_reject,
    verify_password,
)
from app.models.company import Company
from app.models.enums import UserRole
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.services import email_service

RESET_TOKEN_VALID_FOR = timedelta(hours=2)


def register(db: Session, payload: RegisterRequest) -> tuple[User, TokenPair]:
    if db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    if db.query(Company).filter(Company.code == payload.company_code).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Company code already in use")

    company = Company(name=payload.company_name, code=payload.company_code)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.COMPANY_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, issue_tokens(user)


def login(db: Session, payload: LoginRequest) -> tuple[User, TokenPair]:
    # Emails are matched case-insensitively: "John@Site.com" and "john@site.com" are one person.
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")
    if not user.company.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This company's account has been suspended")

    return user, issue_tokens(user)


def refresh(db: Session, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    rotate_refresh_or_reject(payload, "refresh")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active or not user.company.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    return issue_tokens(user)


def issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


def logout(access_token_payload: dict) -> None:
    revoke_token(access_token_payload)


def logout_all(user_id: uuid.UUID) -> None:
    logout_all_sessions("access", str(user_id))


def on_password_changed(user_id: uuid.UUID) -> None:
    """Every existing session must stop working the moment a password
    changes -- otherwise a stolen-but-not-yet-detected session would survive
    the very action meant to lock it out."""
    logout_all_sessions("access", str(user_id))


def on_account_suspended(user_id: uuid.UUID) -> None:
    logout_all_sessions("access", str(user_id))


def request_password_reset(db: Session, email: str) -> None:
    """Always returns without error, whether or not the email matches an
    account -- the caller (the API layer) always responds 204 either way,
    so a requester can never learn which emails have accounts from this
    endpoint's behavior alone."""
    user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
    if not user:
        return
    token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + RESET_TOKEN_VALID_FOR,
    )
    db.add(reset)
    db.commit()
    email_service.send_templated(
        db, "password_reset", user.email,
        {
            "full_name": user.full_name, "valid_hours": int(RESET_TOKEN_VALID_FOR.total_seconds() // 3600),
            "reset_url": f"{get_settings().app_base_url}/reset-password?token={token}",
        },
        dedup_key=f"password-reset:{reset.id}",
    )


def reset_password(db: Session, token: str, new_password: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    reset = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
    now = datetime.now(timezone.utc)
    expires_at = reset.expires_at if reset and reset.expires_at.tzinfo else (reset.expires_at.replace(tzinfo=timezone.utc) if reset else None)
    if not reset or reset.used_at is not None or expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")

    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")

    user.hashed_password = hash_password(new_password)
    reset.used_at = now
    db.commit()
    # Every existing session must die -- the whole point of a password
    # reset is to lock out anyone who had the old password/a stolen session.
    logout_all_sessions("access", str(user.id))
