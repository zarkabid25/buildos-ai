import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.enums import PlatformStaffRole
from app.models.platform_admin import PlatformAdmin
from app.schemas.auth import TokenPair
from app.schemas.platform import (
    PlatformAcceptInvitation,
    PlatformAdminRead,
    PlatformAuditEntry,
    PlatformAuthResponse,
    PlatformCompanyList,
    PlatformCompanyRead,
    PlatformDashboard,
    PlatformInvitationCreate,
    PlatformInvitationCreated,
    PlatformInvitationInfo,
    PlatformInvitationRead,
    PlatformLoginRequest,
    PlatformRefreshRequest,
    PlatformStaffUpdate,
    MarketplaceFlagUpdate,
)
from app.services import platform_audit_service, platform_auth_service, platform_company_service, platform_staff_service

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
def refresh(payload: PlatformRefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    settings = get_settings()
    key = f"platform-refresh:{_client_ip(request)}"
    limiter.check(key, settings.refresh_max_per_ip, settings.refresh_window_seconds, TOO_MANY)
    limiter.hit(key)
    return platform_auth_service.refresh(db, payload.refresh_token)


@router.get("/auth/me", response_model=PlatformAdminRead)
def me(current_admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
    return current_admin


# ---- Public staff invitation routes (mirrors /auth/invitations/{token}, /auth/accept-invite) ----


@router.get("/auth/invitations/{token}", response_model=PlatformInvitationInfo)
def invitation_info(token: str, request: Request, db: Session = Depends(get_db)) -> PlatformInvitationInfo:
    settings = get_settings()
    key = f"platform-invite:{_client_ip(request)}"
    limiter.check(key, settings.register_max_per_ip * 5, settings.register_window_seconds, TOO_MANY)
    limiter.hit(key)
    return platform_staff_service.get_invitation_info(db, token)


@router.post("/auth/accept-invite", response_model=PlatformAuthResponse, status_code=201)
def accept_invite(
    payload: PlatformAcceptInvitation, request: Request, db: Session = Depends(get_db)
) -> PlatformAuthResponse:
    settings = get_settings()
    key = f"platform-register:{_client_ip(request)}"
    limiter.check(key, settings.register_max_per_ip, settings.register_window_seconds, TOO_MANY)
    limiter.hit(key)
    admin = platform_staff_service.accept_invitation(db, payload)
    tokens = platform_auth_service.issue_tokens(admin)
    return PlatformAuthResponse(**tokens.model_dump(), admin=PlatformAdminRead.model_validate(admin))


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


@router.post("/companies/{company_id}/approve", response_model=PlatformCompanyRead)
def approve_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)),
) -> PlatformCompanyRead:
    return platform_company_service.approve_company(db, company_id, admin)


@router.post("/companies/{company_id}/marketplace", response_model=PlatformCompanyRead)
def set_marketplace_enabled(
    company_id: uuid.UUID,
    payload: MarketplaceFlagUpdate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)),
) -> PlatformCompanyRead:
    return platform_company_service.set_marketplace_enabled(db, company_id, payload.enabled, admin)


@router.post("/companies/{company_id}/suspend", response_model=PlatformCompanyRead)
def suspend_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)),
) -> PlatformCompanyRead:
    return platform_company_service.set_company_suspended(db, company_id, suspended=True, actor=admin)


@router.post("/companies/{company_id}/reactivate", response_model=PlatformCompanyRead)
def reactivate_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)),
) -> PlatformCompanyRead:
    return platform_company_service.set_company_suspended(db, company_id, suspended=False, actor=admin)


@router.get("/audit-log", response_model=list[PlatformAuditEntry])
def audit_log(
    db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> list[PlatformAuditEntry]:
    return platform_audit_service.list_entries(db)


# ---- Staff management (PLAT-006/010, owner only) -----------------------------------


@router.get("/staff", response_model=list[PlatformAdminRead])
def list_staff(
    db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> list[PlatformAdminRead]:
    return platform_staff_service.list_staff(db)


@router.patch("/staff/{admin_id}", response_model=PlatformAdminRead)
def update_staff(
    admin_id: uuid.UUID,
    payload: PlatformStaffUpdate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER)),
) -> PlatformAdminRead:
    return platform_staff_service.update_staff(db, admin, admin_id, payload)


@router.post("/staff/invitations", response_model=PlatformInvitationCreated, status_code=201)
def create_staff_invitation(
    payload: PlatformInvitationCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER)),
) -> PlatformInvitationCreated:
    return platform_staff_service.create_invitation(db, admin, payload)


@router.get("/staff/invitations", response_model=list[PlatformInvitationRead])
def list_staff_invitations(
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER)),
) -> list[PlatformInvitationRead]:
    return platform_staff_service.list_invitations(db)


@router.delete("/staff/invitations/{invitation_id}", status_code=204)
def revoke_staff_invitation(
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_roles(PlatformStaffRole.OWNER)),
) -> None:
    platform_staff_service.revoke_invitation(db, admin, invitation_id)
