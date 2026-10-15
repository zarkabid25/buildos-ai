import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.company import Company
from app.models.crm import CrmActivity, CrmContact, CrmOrganization
from app.models.enums import CrmPipelineType, CrmStage
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
from app.services import platform_audit_service

# ---- Organizations -----------------------------------------------------------------


def _owner_names(db: Session, owner_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not owner_ids:
        return {}
    rows = db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(owner_ids)).all()
    return dict(rows)


def _read(org: CrmOrganization, owner_name: str | None) -> CrmOrganizationRead:
    return CrmOrganizationRead(
        id=org.id,
        name=org.name,
        pipeline_type=org.pipeline_type,
        stage=org.stage,
        source=org.source,
        industry=org.industry,
        website=org.website,
        phone=org.phone,
        email=org.email,
        notes=org.notes,
        owner_staff_id=org.owner_staff_id,
        owner_staff_name=owner_name,
        converted_company_id=org.converted_company_id,
        converted_at=org.converted_at,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def create_organization(db: Session, actor: PlatformAdmin, payload: CrmOrganizationCreate) -> CrmOrganizationRead:
    if payload.owner_staff_id and not db.query(PlatformAdmin).filter(PlatformAdmin.id == payload.owner_staff_id).first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assigned staff member not found")

    org = CrmOrganization(
        name=payload.name.strip(),
        pipeline_type=payload.pipeline_type,
        source=payload.source,
        industry=payload.industry,
        website=payload.website,
        phone=payload.phone,
        email=payload.email,
        notes=payload.notes,
        owner_staff_id=payload.owner_staff_id,
    )
    db.add(org)
    db.flush()
    platform_audit_service.record(
        db, actor.id, "crm.lead_created", "crm_organization", org.id,
        f"{org.name} added to the {org.pipeline_type.value} pipeline",
    )
    db.commit()
    db.refresh(org)
    names = _owner_names(db, [org.owner_staff_id] if org.owner_staff_id else [])
    return _read(org, names.get(org.owner_staff_id) if org.owner_staff_id else None)


def list_organizations(
    db: Session, pipeline_type: CrmPipelineType | None = None, owner_staff_id: uuid.UUID | None = None
) -> list[CrmOrganizationRead]:
    query = db.query(CrmOrganization)
    if pipeline_type:
        query = query.filter(CrmOrganization.pipeline_type == pipeline_type)
    if owner_staff_id:
        query = query.filter(CrmOrganization.owner_staff_id == owner_staff_id)
    orgs = query.order_by(CrmOrganization.created_at.desc()).all()
    names = _owner_names(db, [o.owner_staff_id for o in orgs if o.owner_staff_id])
    return [_read(o, names.get(o.owner_staff_id) if o.owner_staff_id else None) for o in orgs]


def get_organization(db: Session, org_id: uuid.UUID) -> CrmOrganizationDetail:
    org = (
        db.query(CrmOrganization)
        .options(selectinload(CrmOrganization.contacts), selectinload(CrmOrganization.activities))
        .filter(CrmOrganization.id == org_id)
        .first()
    )
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CRM organization not found")
    names = _owner_names(db, [org.owner_staff_id] if org.owner_staff_id else [])
    base = _read(org, names.get(org.owner_staff_id) if org.owner_staff_id else None)
    creator_ids = list({a.created_by_id for a in org.activities})
    creator_names = _owner_names(db, creator_ids)
    return CrmOrganizationDetail(
        **base.model_dump(),
        contacts=[CrmContactRead.model_validate(c) for c in org.contacts],
        activities=[
            CrmActivityRead(**CrmActivityRead.model_validate(a).model_dump(exclude={"created_by_name"}), created_by_name=creator_names.get(a.created_by_id))
            for a in org.activities
        ],
    )


def update_organization(
    db: Session, actor: PlatformAdmin, org_id: uuid.UUID, payload: CrmOrganizationUpdate
) -> CrmOrganizationRead:
    org = db.query(CrmOrganization).filter(CrmOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CRM organization not found")

    changes = payload.model_dump(exclude_unset=True)
    if "owner_staff_id" in changes and changes["owner_staff_id"] is not None:
        if not db.query(PlatformAdmin).filter(PlatformAdmin.id == changes["owner_staff_id"]).first():
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Assigned staff member not found")

    before_stage = org.stage
    for field, value in changes.items():
        setattr(org, field, value)

    if "stage" in changes and changes["stage"] != before_stage:
        platform_audit_service.record(
            db, actor.id, "crm.stage_changed", "crm_organization", org.id,
            f"{org.name}: stage {before_stage.value} -> {org.stage.value}",
            {"from": before_stage.value, "to": org.stage.value},
        )
    if "owner_staff_id" in changes:
        platform_audit_service.record(
            db, actor.id, "crm.lead_assigned", "crm_organization", org.id,
            f"{org.name} assigned",
        )

    db.commit()
    db.refresh(org)
    names = _owner_names(db, [org.owner_staff_id] if org.owner_staff_id else [])
    return _read(org, names.get(org.owner_staff_id) if org.owner_staff_id else None)


# ---- Contacts -----------------------------------------------------------------------


def add_contact(db: Session, org_id: uuid.UUID, payload: CrmContactCreate) -> CrmContactRead:
    org = db.query(CrmOrganization).filter(CrmOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CRM organization not found")
    contact = CrmContact(organization_id=org_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return CrmContactRead.model_validate(contact)


# ---- Activities (calls, meetings, notes, reminders) ----------------------------------


def add_activity(db: Session, actor: PlatformAdmin, org_id: uuid.UUID, payload: CrmActivityCreate) -> CrmActivityRead:
    org = db.query(CrmOrganization).filter(CrmOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CRM organization not found")
    activity = CrmActivity(organization_id=org_id, created_by_id=actor.id, **payload.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return CrmActivityRead(**CrmActivityRead.model_validate(activity).model_dump(exclude={"created_by_name"}), created_by_name=actor.full_name)


def complete_activity(db: Session, activity_id: uuid.UUID) -> CrmActivityRead:
    activity = db.query(CrmActivity).filter(CrmActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
    activity.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(activity)
    names = _owner_names(db, [activity.created_by_id])
    return CrmActivityRead(**CrmActivityRead.model_validate(activity).model_dump(exclude={"created_by_name"}), created_by_name=names.get(activity.created_by_id))


def list_follow_ups(db: Session, owner_staff_id: uuid.UUID | None = None) -> list[CrmActivityRead]:
    """The follow-up dashboard: open (uncompleted) tasks with a due date, across
    every organization, soonest first. Overdue ones sort first naturally."""
    query = (
        db.query(CrmActivity, CrmOrganization.name, CrmOrganization.owner_staff_id)
        .join(CrmOrganization, CrmOrganization.id == CrmActivity.organization_id)
        .filter(CrmActivity.due_at.isnot(None), CrmActivity.completed_at.is_(None))
    )
    if owner_staff_id:
        query = query.filter(CrmOrganization.owner_staff_id == owner_staff_id)
    rows = query.order_by(CrmActivity.due_at.asc()).all()
    creator_names = _owner_names(db, [a.created_by_id for a, _, _ in rows])
    return [
        CrmActivityRead(
            **CrmActivityRead.model_validate(a).model_dump(exclude={"created_by_name"}),
            created_by_name=creator_names.get(a.created_by_id),
        )
        for a, _org_name, _owner_id in rows
    ]


# ---- Conversion (PLAT-015) -----------------------------------------------------------


def convert_to_company(
    db: Session, actor: PlatformAdmin, org_id: uuid.UUID, payload: CrmConvertRequest
) -> CrmConvertResult:
    org = db.query(CrmOrganization).filter(CrmOrganization.id == org_id).first()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "CRM organization not found")

    # Idempotent: calling convert again on an already-converted lead returns the
    # existing linkage instead of erroring or creating a second company.
    if org.converted_company_id:
        names = _owner_names(db, [org.owner_staff_id] if org.owner_staff_id else [])
        return CrmConvertResult(
            organization=_read(org, names.get(org.owner_staff_id) if org.owner_staff_id else None),
            company_id=org.converted_company_id,
            already_converted=True,
        )

    has_link = payload.link_existing_company_id is not None
    has_create = bool(payload.create_company_name or payload.create_company_code)
    if has_link == has_create:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Give exactly one of link_existing_company_id or create_company_name/code"
        )

    if has_link:
        company = db.query(Company).filter(Company.id == payload.link_existing_company_id).first()
        if not company:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Company to link not found")
        already_linked = (
            db.query(CrmOrganization)
            .filter(CrmOrganization.converted_company_id == company.id, CrmOrganization.id != org.id)
            .first()
        )
        if already_linked:
            raise HTTPException(status.HTTP_409_CONFLICT, "That company is already linked to another CRM lead")
        action = "crm.lead_converted_linked"
        summary = f"{org.name} linked to existing company {company.name}"
    else:
        if not payload.create_company_name or not payload.create_company_code:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "create_company_name and create_company_code are both required")
        if db.query(Company).filter(Company.code == payload.create_company_code).first():
            raise HTTPException(status.HTTP_409_CONFLICT, "Company code already in use")
        company = Company(name=payload.create_company_name.strip(), code=payload.create_company_code.strip())
        db.add(company)
        db.flush()
        action = "crm.lead_converted_created"
        summary = f"{org.name} converted to new company {company.name}"

    org.converted_company_id = company.id
    org.converted_at = datetime.now(timezone.utc)
    org.stage = CrmStage.WON
    platform_audit_service.record(db, actor.id, action, "crm_organization", org.id, summary, {"company_id": str(company.id)})
    db.commit()
    db.refresh(org)
    names = _owner_names(db, [org.owner_staff_id] if org.owner_staff_id else [])
    return CrmConvertResult(
        organization=_read(org, names.get(org.owner_staff_id) if org.owner_staff_id else None),
        company_id=company.id,
        already_converted=False,
    )
