from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import PasswordChange, UserRead, UserSelfUpdate
from app.services import auth_service, user_service

router = APIRouter(prefix="/auth", tags=["auth"])

TOO_MANY = "Too many attempts. Please wait and try again."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    settings = get_settings()
    key = f"register:{_client_ip(request)}"
    limiter.check(key, settings.register_max_per_ip, settings.register_window_seconds, TOO_MANY)
    limiter.hit(key)
    user, tokens = auth_service.register(db, payload)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> AuthResponse:
    # Only failures count, per address and account, so a typo doesn't lock anyone out
    # but guessing a password is capped. Checked before the password is even looked at.
    settings = get_settings()
    key = f"login:{_client_ip(request)}:{payload.email.lower()}"
    limiter.check(key, settings.login_max_failures, settings.login_failure_window_seconds, TOO_MANY)
    try:
        user, tokens = auth_service.login(db, payload)
    except HTTPException as exc:
        if exc.status_code == 401:
            limiter.hit(key)
        raise
    limiter.reset(key)
    return AuthResponse(**tokens.model_dump(), user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return auth_service.refresh(db, payload.refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserSelfUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    return user_service.update_me(db, current_user, payload)


@router.post("/me/password", status_code=204)
def change_password(
    payload: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    # A stolen session shouldn't be able to guess its way to the real password either.
    settings = get_settings()
    key = f"password:{current_user.id}"
    limiter.check(key, settings.login_max_failures, settings.login_failure_window_seconds, TOO_MANY)
    try:
        user_service.change_password(db, current_user, payload)
    except HTTPException as exc:
        if exc.status_code == 400:
            limiter.hit(key)
        raise
    limiter.reset(key)
