"""Supplier dashboard and profile (PLAT-039). Metrics are plain counts over
real rows -- the same existing tables every other part of this app already
reads (MarketplaceRfqInvitation, MarketplaceQuotationAttribution,
MarketplacePoAttribution, MarketplaceDeliveryReport, CommissionInvoice) --
never a separately-tracked number that could drift from the truth."""

import uuid
from datetime import date

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.storage import DOCUMENT_TYPES, save_upload
from app.models.commission import CommissionInvoice, MarketplacePoAttribution
from app.models.enums import CommissionInvoiceStatus, PurchaseOrderStatus
from app.models.marketplace_supplier import (
    MarketplaceDeliveryReport,
    MarketplaceQuotationAttribution,
    MarketplaceRfqInvitation,
    MarketplaceSupplier,
    MarketplaceSupplierCategory,
    MarketplaceSupplierCoverageArea,
    MarketplaceSupplierDocument,
)
from app.models.procurement import PurchaseOrder
from app.schemas.supplier_portal import SupplierDashboard, SupplierDocumentRead, SupplierProfileRead, SupplierProfileUpdate

ACTIVE_ORDER_STATUSES = (PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED)


def get_dashboard(db: Session, marketplace_supplier_id: uuid.UUID) -> SupplierDashboard:
    invited_count = db.query(MarketplaceRfqInvitation).filter(MarketplaceRfqInvitation.marketplace_supplier_id == marketplace_supplier_id, MarketplaceRfqInvitation.status == "invited").count()
    submitted_count = db.query(MarketplaceQuotationAttribution).filter(MarketplaceQuotationAttribution.marketplace_supplier_id == marketplace_supplier_id).count()

    active_pos = (
        db.query(MarketplacePoAttribution, PurchaseOrder)
        .join(PurchaseOrder, PurchaseOrder.id == MarketplacePoAttribution.purchase_order_id)
        .filter(MarketplacePoAttribution.marketplace_supplier_id == marketplace_supplier_id, PurchaseOrder.status.in_(ACTIVE_ORDER_STATUSES))
        .all()
    )
    active_po_ids = [po.id for _a, po in active_pos]
    reported_po_ids = set()
    if active_po_ids:
        reported_po_ids = {
            r[0] for r in db.query(MarketplaceDeliveryReport.purchase_order_id).filter(MarketplaceDeliveryReport.purchase_order_id.in_(active_po_ids)).all()
        }
    pending_delivery = len([pid for pid in active_po_ids if pid not in reported_po_ids])

    outstanding_invoices = (
        db.query(CommissionInvoice)
        .filter(CommissionInvoice.marketplace_supplier_id == marketplace_supplier_id, CommissionInvoice.status.in_([CommissionInvoiceStatus.PENDING, CommissionInvoiceStatus.PARTIALLY_PAID]))
        .count()
    )

    return SupplierDashboard(
        new_invitations=invited_count,
        pending_quotations=invited_count,  # awaiting a response, same set as "new invitations"
        submitted_quotations=submitted_count,
        active_linked_orders=len(active_po_ids),
        pending_delivery_updates=pending_delivery,
        outstanding_commission_invoices=outstanding_invoices,
    )


def _get_supplier(db: Session, marketplace_supplier_id: uuid.UUID) -> MarketplaceSupplier:
    supplier = (
        db.query(MarketplaceSupplier)
        .options(selectinload(MarketplaceSupplier.categories), selectinload(MarketplaceSupplier.coverage_areas))
        .filter(MarketplaceSupplier.id == marketplace_supplier_id)
        .first()
    )
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


def get_profile(db: Session, marketplace_supplier_id: uuid.UUID) -> SupplierProfileRead:
    supplier = _get_supplier(db, marketplace_supplier_id)
    return SupplierProfileRead(
        id=supplier.id, name=supplier.name, legal_name=supplier.legal_name, email=supplier.email, phone=supplier.phone,
        website=supplier.website, address=supplier.address, notes=supplier.notes, verification_status=supplier.verification_status,
        categories=[c.category for c in supplier.categories], coverage_areas=[a.area for a in supplier.coverage_areas],
    )


def update_profile(db: Session, marketplace_supplier_id: uuid.UUID, payload: SupplierProfileUpdate) -> SupplierProfileRead:
    """Deliberately reimplements (rather than calls) marketplace_supplier_service.update_supplier:
    that function also accepts name/legal_name, which must never be settable
    from the supplier side (PLAT-039 -- legal/verification info stays on the
    staff workflow). Scoping the editable field set here is what actually
    enforces that, not a comment."""
    supplier = _get_supplier(db, marketplace_supplier_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"categories", "coverage_areas"})
    for field, value in changes.items():
        setattr(supplier, field, value)

    if payload.categories is not None:
        for c in list(supplier.categories):
            db.delete(c)
        db.flush()
        for cat in dict.fromkeys(c.strip() for c in payload.categories if c.strip()):
            db.add(MarketplaceSupplierCategory(supplier_id=supplier.id, category=cat))
    if payload.coverage_areas is not None:
        for a in list(supplier.coverage_areas):
            db.delete(a)
        db.flush()
        for area in dict.fromkeys(a.strip() for a in payload.coverage_areas if a.strip()):
            db.add(MarketplaceSupplierCoverageArea(supplier_id=supplier.id, area=area))

    db.commit()
    db.refresh(supplier)
    return get_profile(db, marketplace_supplier_id)


def list_documents(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupplierDocumentRead]:
    rows = db.query(MarketplaceSupplierDocument).filter(MarketplaceSupplierDocument.supplier_id == marketplace_supplier_id).order_by(MarketplaceSupplierDocument.created_at.desc()).all()
    return [SupplierDocumentRead.model_validate(d) for d in rows]


async def upload_document(db: Session, marketplace_supplier_id: uuid.UUID, supplier_user_id: uuid.UUID, file: UploadFile, title: str) -> SupplierDocumentRead:
    _get_supplier(db, marketplace_supplier_id)
    key, size = await save_upload(file, marketplace_supplier_id, "marketplace-suppliers", DOCUMENT_TYPES)
    document = MarketplaceSupplierDocument(
        supplier_id=marketplace_supplier_id,
        title=title.strip() or (file.filename or "Untitled"),
        original_filename=(file.filename or "document")[:255],
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        storage_key=key,
        uploaded_by_supplier_user_id=supplier_user_id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return SupplierDocumentRead.model_validate(document)
