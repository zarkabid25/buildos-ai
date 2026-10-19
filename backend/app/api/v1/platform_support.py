import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.db.session import get_db
from app.models.enums import PlatformStaffRole, SupplierApplicationStatus, SupportTicketStatus
from app.models.platform_admin import PlatformAdmin
from app.schemas.public_site import SupplierApplicationDocumentRead, SupplierApplicationRead, SupplierApplicationReview
from app.schemas.support import SupportTicketMessageCreate, SupportTicketRead, SupportTicketSummary, SupportTicketUpdate
from app.services import platform_notification_service, public_site_service, support_ticket_service

router = APIRouter(prefix="/platform", tags=["platform-support"])

_can_edit = require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)


# ---- PLAT-045: supplier application review -----------------------------------------------------


@router.get("/supplier-applications", response_model=list[SupplierApplicationRead])
def list_supplier_applications(status: SupplierApplicationStatus | None = None, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SupplierApplicationRead]:
    return public_site_service.list_applications(db, status)


@router.get("/supplier-applications/{application_id}", response_model=SupplierApplicationRead)
def get_supplier_application(application_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> SupplierApplicationRead:
    return public_site_service.get_application(db, application_id)


@router.get("/supplier-applications/{application_id}/documents", response_model=list[SupplierApplicationDocumentRead])
def list_supplier_application_documents(application_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SupplierApplicationDocumentRead]:
    return public_site_service.list_application_documents(db, application_id)


@router.get("/supplier-applications/{application_id}/documents/{document_id}/download")
def download_supplier_application_document(application_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)):
    from fastapi.responses import FileResponse

    from app.core.storage import resolve_path

    document = public_site_service.get_application_document(db, application_id, document_id)
    return FileResponse(resolve_path(document.storage_key), media_type=document.content_type, filename=document.original_filename)


@router.post("/supplier-applications/{application_id}/review", response_model=SupplierApplicationRead)
def review_supplier_application(application_id: uuid.UUID, payload: SupplierApplicationReview, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SupplierApplicationRead:
    return public_site_service.review_application(db, admin, application_id, payload.approve, payload.review_notes)


# ---- PLAT-046: support desk (staff side) --------------------------------------------------------


@router.get("/support", response_model=list[SupportTicketSummary])
def list_all_tickets(status: SupportTicketStatus | None = None, assigned_staff_id: uuid.UUID | None = None, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SupportTicketSummary]:
    return support_ticket_service.list_all_tickets(db, status, assigned_staff_id)


@router.get("/support/{ticket_id}", response_model=SupportTicketRead)
def get_ticket(ticket_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> SupportTicketRead:
    return support_ticket_service.get_ticket_for_staff(db, ticket_id)


@router.patch("/support/{ticket_id}", response_model=SupportTicketRead)
def update_ticket(ticket_id: uuid.UUID, payload: SupportTicketUpdate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SupportTicketRead:
    return support_ticket_service.update_ticket(db, admin, ticket_id, payload)


@router.post("/support/{ticket_id}/messages", response_model=SupportTicketRead, status_code=201)
def reply_ticket(ticket_id: uuid.UUID, payload: SupportTicketMessageCreate, is_internal: bool = False, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SupportTicketRead:
    return support_ticket_service.reply_as_staff(db, admin, ticket_id, payload.body, is_internal)


# ---- PLAT-047: platform notification feed -------------------------------------------------------


@router.get("/notifications")
def list_platform_notifications(include_dismissed: bool = False, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)):
    rows = platform_notification_service.list_notifications(db, include_dismissed)
    return [
        {"id": n.id, "notification_type": n.notification_type, "title": n.title, "body": n.body, "link": n.link, "dismissed_at": n.dismissed_at, "created_at": n.created_at}
        for n in rows
    ]


@router.post("/notifications/{notification_id}/dismiss")
def dismiss_platform_notification(notification_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)):
    platform_notification_service.dismiss(db, notification_id)
    return {"ok": True}
