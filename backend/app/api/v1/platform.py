import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.platform_admin import PlatformAdmin
from app.schemas.auth import TokenPair
from app.schemas.platform import (
    PlatformAdminRead,
    PlatformAuthResponse,
    PlatformCompanyList,
    PlatformCompanyRead,
    PlatformDashboard,
    PlatformLoginRequest,
    PlatformRefreshRequest,
)
from app.services import platform_auth_service, platform_company_service

router = APIRouter(prefix="/platform", tags=["platform"])

TOO_MANY = "Too many attempts. Please wait and try again."


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/auth/login", response_model=PlatformAuthResponse)
def login(payload: PlatformLoginRequest, request: Request, db: Session = Depends(get_db)) -> PlatformAuthResponse:
    settings = get_settings()
    key = f"platform-login:{_client_ip(request)}:{payload.email.lower()}"
    limiter.check(key, settings.login_max_failures, settings.login_failure_window_seconds, TOO_MANY)
    try:
        admin, tokens = platform_auth_service.login(db, payload)
    except HTTPException as exc:
        if exc.status_code == 401:
            limiter.hit(key)
        raise
    limiter.reset(key)
    return PlatformAuthResponse(**tokens.model_dump(), admin=PlatformAdminRead.model_validate(admin))


@router.post("/auth/refresh", response_model=TokenPair)
def refresh(payload: PlatformRefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    return platform_auth_service.refresh(db, payload.refresh_token)


@router.get("/auth/me", response_model=PlatformAdminRead)
def me(current_admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
    return current_admin


@router.get("/dashboard", response_model=PlatformDashboard)
def dashboard(
    db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> PlatformDashboard:
    return platform_company_service.dashboard(db)


@router.get("/companies", response_model=PlatformCompanyList)
def list_companies(
    search: str | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> PlatformCompanyList:
    return platform_company_service.list_companies(db, search)


@router.get("/companies/{company_id}", response_model=PlatformCompanyRead)
def get_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> PlatformCompanyRead:
    return platform_company_service.get_company(db, company_id)


@router.post("/companies/{company_id}/suspend", response_model=PlatformCompanyRead)
def suspend_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> PlatformCompanyRead:
    return platform_company_service.set_company_suspended(db, company_id, suspended=True)


@router.post("/companies/{company_id}/reactivate", response_model=PlatformCompanyRead)
def reactivate_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> PlatformCompanyRead:
    return platform_company_service.set_company_suspended(db, company_id, suspended=False)
