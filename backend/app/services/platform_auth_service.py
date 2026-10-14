import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import (
    create_platform_access_token,
    create_platform_refresh_token,
    decode_token,
    verify_password,
)
from app.models.platform_admin import PlatformAdmin
from app.schemas.auth import TokenPair
from app.schemas.platform import PlatformLoginRequest


def login(db: Session, payload: PlatformLoginRequest) -> tuple[PlatformAdmin, TokenPair]:
    admin = db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == payload.email.lower()).first()
    if not admin or not verify_password(payload.password, admin.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Platform admin account is disabled")

    return admin, issue_tokens(admin)


def refresh(db: Session, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "platform_refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    try:
        admin_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    return issue_tokens(admin)


def issue_tokens(admin: PlatformAdmin) -> TokenPair:
    return TokenPair(
        access_token=create_platform_access_token(str(admin.id)),
        refresh_token=create_platform_refresh_token(str(admin.id)),
    )
