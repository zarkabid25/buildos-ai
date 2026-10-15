import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.db.session import get_db
from app.models.enums import CrmPipelineType, PlatformStaffRole
from app.models.platform_admin import PlatformAdmin
from app.schemas.crm import (
    CrmActivityCreate,
    CrmActivityRead,
    CrmContactCreate,
    CrmContactRead,
    CrmConvertRequest,
    CrmConvertResult,
    CrmOrganizationCreate,
    CrmOrganizationDetail,
    CrmOrganizationRead,
    CrmOrganizationUpdate,
)
from app.services import crm_service

router = APIRouter(prefix="/platform/crm", tags=["platform-crm"])

# Viewing is open to every active platform staff member (including support);
# mutating a lead's record requires owner or admin, same tier as company approval.
_can_edit = require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)


@router.get("/organizations", response_model=list[CrmOrganizationRead])
def list_organizations(
    pipeline_type: CrmPipelineType | None = None,
    owner_staff_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[CrmOrganizationRead]:
    return crm_service.list_organizations(db, pipeline_type, owner_staff_id)


@router.post("/organizations", response_model=CrmOrganizationRead, status_code=201)
def create_organization(
    payload: CrmOrganizationCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)
) -> CrmOrganizationRead:
    return crm_service.create_organization(db, admin, payload)


@router.get("/organizations/{org_id}", response_model=CrmOrganizationDetail)
def get_organization(
    org_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> CrmOrganizationDetail:
    return crm_service.get_organization(db, org_id)


@router.patch("/organizations/{org_id}", response_model=CrmOrganizationRead)
def update_organization(
    org_id: uuid.UUID,
    payload: CrmOrganizationUpdate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> CrmOrganizationRead:
    return crm_service.update_organization(db, admin, org_id, payload)


@router.post("/organizations/{org_id}/contacts", response_model=CrmContactRead, status_code=201)
def add_contact(
    org_id: uuid.UUID, payload: CrmContactCreate, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(_can_edit)
) -> CrmContactRead:
    return crm_service.add_contact(db, org_id, payload)


@router.post("/organizations/{org_id}/activities", response_model=CrmActivityRead, status_code=201)
def add_activity(
    org_id: uuid.UUID,
    payload: CrmActivityCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> CrmActivityRead:
    # Logging a call/meeting/note is allowed for any active staff, including support.
    return crm_service.add_activity(db, admin, org_id, payload)


@router.post("/activities/{activity_id}/complete", response_model=CrmActivityRead)
def complete_activity(
    activity_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> CrmActivityRead:
    return crm_service.complete_activity(db, activity_id)


@router.get("/follow-ups", response_model=list[CrmActivityRead])
def follow_ups(
    owner_staff_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[CrmActivityRead]:
    return crm_service.list_follow_ups(db, owner_staff_id)


@router.post("/organizations/{org_id}/convert", response_model=CrmConvertResult)
def convert_organization(
    org_id: uuid.UUID,
    payload: CrmConvertRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> CrmConvertResult:
    return crm_service.convert_to_company(db, admin, org_id, payload)
