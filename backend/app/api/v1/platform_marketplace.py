import uuid

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.core.storage import resolve_path
from app.db.session import get_db
from app.models.enums import MarketplaceSupplierStatus, PlatformStaffRole
from app.models.platform_admin import PlatformAdmin
from app.schemas.marketplace_supplier import (
    MarketplaceCompanyLinkCreate,
    MarketplaceCompanyLinkRead,
    MarketplaceMaterialMappingCreate,
    MarketplaceMaterialMappingRead,
    MarketplaceProductCreate,
    MarketplaceProductRead,
    MarketplaceProductUpdate,
    MarketplaceSupplierContactCreate,
    MarketplaceSupplierContactRead,
    MarketplaceSupplierCreate,
    MarketplaceSupplierCreated,
    MarketplaceSupplierDetail,
    MarketplaceSupplierDocumentRead,
    MarketplaceSupplierList,
    MarketplaceSupplierRead,
    MarketplaceSupplierUpdate,
    MarketplaceVerificationUpdate,
)
from app.schemas.marketplace_integration import (
    DeliveryReportCreate,
    DeliveryReportRead,
    InviteSuppliersRequest,
    MarketplaceInvitationRead,
    MarketplaceOrderStatus,
    SupplierMatch,
)
from app.schemas.platform import PlatformAuditEntry
from app.schemas.rfq import QuotationCreate, RfqRead
from app.services import marketplace_integration_service, marketplace_supplier_service, rfq_service

router = APIRouter(prefix="/platform/marketplace", tags=["platform-marketplace"])

# Same tier as CRM and company approval: support can view and search, not mutate.
_can_edit = require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)


@router.post("/suppliers", response_model=MarketplaceSupplierCreated, status_code=201)
def create_supplier(
    payload: MarketplaceSupplierCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)
) -> MarketplaceSupplierCreated:
    return marketplace_supplier_service.create_supplier(db, admin, payload)


@router.get("/suppliers", response_model=MarketplaceSupplierList)
def list_suppliers(
    search: str | None = None,
    category: str | None = None,
    area: str | None = None,
    verification_status: MarketplaceSupplierStatus | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> MarketplaceSupplierList:
    return marketplace_supplier_service.list_suppliers(db, search, category, area, verification_status)


@router.get("/suppliers/{supplier_id}", response_model=MarketplaceSupplierDetail)
def get_supplier(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> MarketplaceSupplierDetail:
    return marketplace_supplier_service.get_supplier(db, supplier_id)


@router.patch("/suppliers/{supplier_id}", response_model=MarketplaceSupplierRead)
def update_supplier(
    supplier_id: uuid.UUID,
    payload: MarketplaceSupplierUpdate,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceSupplierRead:
    return marketplace_supplier_service.update_supplier(db, supplier_id, payload)


@router.post("/suppliers/{supplier_id}/verification", response_model=MarketplaceSupplierRead)
def set_verification_status(
    supplier_id: uuid.UUID,
    payload: MarketplaceVerificationUpdate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceSupplierRead:
    return marketplace_supplier_service.set_verification_status(db, admin, supplier_id, payload)


@router.get("/suppliers/{supplier_id}/activity", response_model=list[PlatformAuditEntry])
def supplier_activity(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> list[PlatformAuditEntry]:
    return marketplace_supplier_service.activity_history(db, supplier_id)


@router.post("/suppliers/{supplier_id}/contacts", response_model=MarketplaceSupplierContactRead, status_code=201)
def add_contact(
    supplier_id: uuid.UUID,
    payload: MarketplaceSupplierContactCreate,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceSupplierContactRead:
    return marketplace_supplier_service.add_contact(db, supplier_id, payload)


@router.post("/suppliers/{supplier_id}/documents", response_model=MarketplaceSupplierDocumentRead, status_code=201)
async def upload_document(
    supplier_id: uuid.UUID,
    file: UploadFile,
    title: str = Form(min_length=1, max_length=255),
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceSupplierDocumentRead:
    return await marketplace_supplier_service.upload_document(db, admin, supplier_id, file, title)


@router.get("/suppliers/{supplier_id}/documents/{document_id}/download")
def download_document(
    supplier_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> FileResponse:
    document = marketplace_supplier_service.get_document(db, supplier_id, document_id)
    path = resolve_path(document.storage_key)
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.post("/suppliers/{supplier_id}/products", response_model=MarketplaceProductRead, status_code=201)
def add_product(
    supplier_id: uuid.UUID,
    payload: MarketplaceProductCreate,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceProductRead:
    return marketplace_supplier_service.add_product(db, supplier_id, payload)


@router.patch("/products/{product_id}", response_model=MarketplaceProductRead)
def update_product(
    product_id: uuid.UUID,
    payload: MarketplaceProductUpdate,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceProductRead:
    return marketplace_supplier_service.update_product(db, product_id, payload)


@router.post("/suppliers/{supplier_id}/company-links", response_model=MarketplaceCompanyLinkRead, status_code=201)
def link_company(
    supplier_id: uuid.UUID,
    payload: MarketplaceCompanyLinkCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceCompanyLinkRead:
    return marketplace_supplier_service.link_company(db, admin, supplier_id, payload)


@router.get("/suppliers/{supplier_id}/company-links", response_model=list[MarketplaceCompanyLinkRead])
def list_company_links(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)
) -> list[MarketplaceCompanyLinkRead]:
    return marketplace_supplier_service.list_company_links(db, supplier_id)


@router.post("/material-mappings", response_model=MarketplaceMaterialMappingRead, status_code=201)
def create_material_mapping(
    payload: MarketplaceMaterialMappingCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> MarketplaceMaterialMappingRead:
    return marketplace_supplier_service.create_material_mapping(db, admin, payload)


# ---- PLAT-023/024/026: platform staff assisting a specific company ----------------------
# Every endpoint below takes company_id explicitly, since platform staff aren't
# scoped to one tenant -- but every call still goes through the same tenant-
# isolated service functions (rfq_service.get_rfq, procurement_service.get_
# purchase_order) that company users themselves go through, so a staff member
# can't be tricked into leaking one company's RFQ into another's view either.


@router.post("/companies/{company_id}/rfqs/{rfq_id}/invite-suppliers", response_model=list[MarketplaceInvitationRead], status_code=201)
def assist_invite_suppliers(
    company_id: uuid.UUID,
    rfq_id: uuid.UUID,
    payload: InviteSuppliersRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> list[MarketplaceInvitationRead]:
    return marketplace_integration_service.invite_suppliers(
        db, company_id, rfq_id, payload.marketplace_supplier_ids, actor_staff_id=admin.id
    )


@router.post(
    "/companies/{company_id}/rfqs/{rfq_id}/suppliers/{marketplace_supplier_id}/quotations",
    response_model=RfqRead,
    status_code=201,
)
def assist_record_quotation(
    company_id: uuid.UUID,
    rfq_id: uuid.UUID,
    marketplace_supplier_id: uuid.UUID,
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> RfqRead:
    rfq = marketplace_integration_service.record_quotation_for_marketplace_supplier(
        db, admin.id, company_id, rfq_id, marketplace_supplier_id, payload
    )
    return rfq_service.to_read(db, company_id, rfq)


@router.get("/companies/{company_id}/purchase-orders/{po_id}/status", response_model=MarketplaceOrderStatus)
def order_status(
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> MarketplaceOrderStatus:
    return marketplace_integration_service.get_order_status(db, company_id, po_id)


@router.post("/companies/{company_id}/purchase-orders/{po_id}/delivery-reports", response_model=DeliveryReportRead, status_code=201)
def report_delivery(
    company_id: uuid.UUID,
    po_id: uuid.UUID,
    payload: DeliveryReportCreate,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(_can_edit),
) -> DeliveryReportRead:
    return marketplace_integration_service.report_delivery(db, admin.id, company_id, po_id, payload)


# ---- PLAT-027: deterministic supplier matching -------------------------------------------


@router.get("/companies/{company_id}/match", response_model=list[SupplierMatch])
def find_eligible_suppliers(
    company_id: uuid.UUID,
    material_id: uuid.UUID,
    area: str | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[SupplierMatch]:
    return marketplace_integration_service.find_eligible_suppliers(db, company_id, material_id, area)
