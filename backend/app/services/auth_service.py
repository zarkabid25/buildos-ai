from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.company import Company
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


def register(db: Session, payload: RegisterRequest) -> tuple[User, TokenPair]:
    if db.query(User).filter(User.email == payload.email).first():
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

    return user, _issue_tokens(user)


def login(db: Session, payload: LoginRequest) -> tuple[User, TokenPair]:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")

    return user, _issue_tokens(user)


def refresh(db: Session, refresh_token: str) -> TokenPair:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    return _issue_tokens(user)


def _issue_tokens(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
