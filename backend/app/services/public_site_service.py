"""Public website lead capture (Phase 8, PLAT-044/045) -- the only two
endpoints in this entire app with no auth dependency at all and a real
write path. Both reuse existing destination systems (CrmOrganization,
MarketplaceSupplier via the unmodified create_supplier) rather than
inventing parallel ones, and neither auto-elevates anything: a demo request
is just a lead; a supplier application stays pending until a real staff
member reviews it."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.storage import DOCUMENT_TYPES, save_upload
from app.models.crm import CrmOrganization
from app.models.enums import CrmPipelineType, SupplierApplicationStatus
from app.models.platform_admin import PlatformAdmin
from app.models.public_site import DemoRequest, SupplierApplication, SupplierApplicationDocument
from app.schemas.marketplace_supplier import MarketplaceSupplierCreate
from app.schemas.public_site import (
    DemoRequestCreate,
    DemoRequestRead,
    SupplierApplicationCreate,
    SupplierApplicationDocumentRead,
    SupplierApplicationRead,
)
from app.services import email_service, marketplace_supplier_service, platform_notification_service

DUPLICATE_WINDOW = timedelta(hours=24)


def _demo_read(d: DemoRequest, already_submitted: bool = False) -> DemoRequestRead:
    return DemoRequestRead(
        id=d.id, full_name=d.full_name, email=d.email, phone=d.phone, company_name=d.company_name,
        message=d.message, crm_organization_id=d.crm_organization_id, already_submitted=already_submitted, created_at=d.created_at,
    )


def create_demo_request(db: Session, payload: DemoRequestCreate) -> DemoRequestRead:
    """Duplicate-submission protection: the same email within the last 24h
    reuses its existing DemoRequest/CrmOrganization rather than creating a
    second one (so a double-click or retried request never creates two
    leads)."""
    email = payload.email.strip().lower()
    cutoff = datetime.now(timezone.utc) - DUPLICATE_WINDOW
    existing = (
        db.query(DemoRequest)
        .filter(func.lower(DemoRequest.email) == email, DemoRequest.created_at >= cutoff)
        .order_by(DemoRequest.created_at.desc())
        .first()
    )
    if existing:
        return _demo_read(existing, already_submitted=True)

    # Reuse an existing lead for this email/company rather than duplicating
    # the organization (PLAT-044's explicit requirement).
    org = (
        db.query(CrmOrganization)
        .filter(CrmOrganization.pipeline_type == CrmPipelineType.SAAS_SALES, func.lower(CrmOrganization.email) == email)
        .first()
    )
    if not org:
        org = CrmOrganization(
            name=payload.company_name.strip(),
            pipeline_type=CrmPipelineType.SAAS_SALES,
            source="website_demo_request",
            email=email,
            phone=payload.phone,
            notes=payload.message,
        )
        db.add(org)
        db.flush()

    demo = DemoRequest(
        full_name=payload.full_name.strip(), email=email, phone=payload.phone,
        company_name=payload.company_name.strip(), message=payload.message, crm_organization_id=org.id,
    )
    db.add(demo)
    db.flush()
    platform_notification_service.notify_staff(
        db, "demo_request_received", f"Demo requested by {payload.full_name} ({payload.company_name})", link="/platform-admin/crm",
    )
    db.commit()
    db.refresh(demo)
    return _demo_read(demo)


def _application_read(app_row: SupplierApplication, staff_name: str | None = None, document_count: int = 0) -> SupplierApplicationRead:
    return SupplierApplicationRead(
        id=app_row.id, business_name=app_row.business_name, contact_name=app_row.contact_name, email=app_row.email, phone=app_row.phone,
        business_registration_info=app_row.business_registration_info,
        categories=[c.strip() for c in (app_row.categories or "").split(",") if c.strip()],
        delivery_locations=[a.strip() for a in (app_row.delivery_locations or "").split(",") if a.strip()],
        business_description=app_row.business_description, status=app_row.status, review_notes=app_row.review_notes,
        reviewed_by_staff_id=app_row.reviewed_by_staff_id, reviewed_by_staff_name=staff_name, reviewed_at=app_row.reviewed_at,
        marketplace_supplier_id=app_row.marketplace_supplier_id, document_count=document_count, created_at=app_row.created_at,
    )


def create_supplier_application(db: Session, payload: SupplierApplicationCreate) -> SupplierApplicationRead:
    application = SupplierApplication(
        business_name=payload.business_name.strip(), contact_name=payload.contact_name.strip(), email=payload.email.strip().lower(),
        phone=payload.phone, business_registration_info=payload.business_registration_info,
        categories=", ".join(c.strip() for c in payload.categories if c.strip()) or None,
        delivery_locations=", ".join(a.strip() for a in payload.delivery_locations if a.strip()) or None,
        business_description=payload.business_description,
    )
    db.add(application)
    db.flush()
    platform_notification_service.notify_staff(
        db, "supplier_application_received", f"Supplier application: {payload.business_name}", link="/platform-admin/supplier-applications",
    )
    db.commit()
    db.refresh(application)
    return _application_read(application)


async def upload_application_document(db: Session, application_id: uuid.UUID, file: UploadFile, title: str) -> SupplierApplicationDocumentRead:
    application = db.query(SupplierApplication).filter(SupplierApplication.id == application_id).first()
    if not application:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    key, size = await save_upload(file, application_id, "supplier-applications", DOCUMENT_TYPES)
    document = SupplierApplicationDocument(
        application_id=application_id, title=title.strip() or (file.filename or "Untitled"),
        original_filename=(file.filename or "document")[:255], content_type=file.content_type or "application/octet-stream",
        size_bytes=size, storage_key=key,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return SupplierApplicationDocumentRead.model_validate(document)


def _staff_names(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    ids = [i for i in ids if i]
    if not ids:
        return {}
    return dict(db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(ids)).all())


def _document_counts(db: Session, application_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not application_ids:
        return {}
    rows = (
        db.query(SupplierApplicationDocument.application_id, func.count(SupplierApplicationDocument.id))
        .filter(SupplierApplicationDocument.application_id.in_(application_ids))
        .group_by(SupplierApplicationDocument.application_id)
        .all()
    )
    return dict(rows)


def list_applications(db: Session, status_filter: SupplierApplicationStatus | None = None) -> list[SupplierApplicationRead]:
    query = db.query(SupplierApplication)
    if status_filter:
        query = query.filter(SupplierApplication.status == status_filter)
    rows = query.order_by(SupplierApplication.created_at.desc()).all()
    staff_names = _staff_names(db, [a.reviewed_by_staff_id for a in rows])
    doc_counts = _document_counts(db, [a.id for a in rows])
    return [_application_read(a, staff_names.get(a.reviewed_by_staff_id), doc_counts.get(a.id, 0)) for a in rows]


def get_application(db: Session, application_id: uuid.UUID) -> SupplierApplicationRead:
    application = db.query(SupplierApplication).filter(SupplierApplication.id == application_id).first()
    if not application:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    staff_names = _staff_names(db, [application.reviewed_by_staff_id])
    doc_count = _document_counts(db, [application.id]).get(application.id, 0)
    return _application_read(application, staff_names.get(application.reviewed_by_staff_id), doc_count)


def list_application_documents(db: Session, application_id: uuid.UUID) -> list[SupplierApplicationDocumentRead]:
    rows = db.query(SupplierApplicationDocument).filter(SupplierApplicationDocument.application_id == application_id).order_by(SupplierApplicationDocument.created_at.desc()).all()
    return [SupplierApplicationDocumentRead.model_validate(d) for d in rows]


def get_application_document(db: Session, application_id: uuid.UUID, document_id: uuid.UUID) -> SupplierApplicationDocument:
    document = db.query(SupplierApplicationDocument).filter(SupplierApplicationDocument.application_id == application_id, SupplierApplicationDocument.id == document_id).first()
    if not document:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def review_application(db: Session, actor: PlatformAdmin, application_id: uuid.UUID, approve: bool, review_notes: str) -> SupplierApplicationRead:
    """Approving an application never auto-verifies a supplier (PLAT-045's
    explicit requirement): it only creates a MarketplaceSupplier through the
    existing, unmodified create_supplier -- which always starts PENDING
    verification, exactly like a staff-entered supplier. A separate,
    already-existing set_verification_status call is still required before
    the supplier can be invited to the portal."""
    application = db.query(SupplierApplication).filter(SupplierApplication.id == application_id).first()
    if not application:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if application.status != SupplierApplicationStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This application was already {application.status.value}")

    if approve:
        created = marketplace_supplier_service.create_supplier(
            db, actor,
            MarketplaceSupplierCreate(
                name=application.business_name, email=application.email, phone=application.phone,
                notes=application.business_description,
                categories=[c.strip() for c in (application.categories or "").split(",") if c.strip()],
                coverage_areas=[a.strip() for a in (application.delivery_locations or "").split(",") if a.strip()],
            ),
        )
        application.marketplace_supplier_id = created.supplier.id
        application.status = SupplierApplicationStatus.APPROVED
    else:
        application.status = SupplierApplicationStatus.REJECTED

    application.review_notes = review_notes
    application.reviewed_by_staff_id = actor.id
    application.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)
    email_service.send_templated(
        db, "supplier_onboarding", application.email,
        {
            "contact_name": application.contact_name, "supplier_name": application.business_name,
            "status": application.status.value,
            "detail": review_notes or ("A platform team member will follow up with next steps." if approve else ""),
        },
        dedup_key=f"supplier-application-review:{application.id}",
    )
    return get_application(db, application.id)
