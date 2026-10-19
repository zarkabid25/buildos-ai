"""Supplier-side order visibility and delivery progress reporting (PLAT-042).
A supplier may only ever see purchase orders that carry a real
MarketplacePoAttribution row for its own marketplace_supplier_id -- the same
single source of truth Phase 6's commission ledger uses, reused here rather
than re-derived. Delivery updates reuse MarketplaceDeliveryReport exactly as
it already exists: deliberately inert, never touching InventoryTransaction
or PurchaseOrderItem.quantity_received -- real stock only ever moves through
procurement_service.create_goods_receipt, which this module never calls."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.commission import MarketplacePoAttribution
from app.models.company import Company
from app.models.marketplace_supplier import MarketplaceDeliveryReport
from app.models.material import Material
from app.models.procurement import PurchaseOrder
from app.schemas.supplier_portal import SupplierDeliveryUpdateCreate, SupplierDeliveryUpdateRead, SupplierOrderItemRead, SupplierOrderRead


def list_orders(db: Session, marketplace_supplier_id: uuid.UUID) -> list[SupplierOrderRead]:
    rows = (
        db.query(MarketplacePoAttribution, PurchaseOrder, Company.name)
        .join(PurchaseOrder, PurchaseOrder.id == MarketplacePoAttribution.purchase_order_id)
        .join(Company, Company.id == MarketplacePoAttribution.company_id)
        .options(selectinload(PurchaseOrder.items))
        .filter(MarketplacePoAttribution.marketplace_supplier_id == marketplace_supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )
    return [_read(po, company_name, db) for _a, po, company_name in rows]


def _read(po: PurchaseOrder, company_name: str, db: Session) -> SupplierOrderRead:
    material_names = dict(db.query(Material.id, Material.name).filter(Material.id.in_([i.material_id for i in po.items])).all()) if po.items else {}
    return SupplierOrderRead(
        purchase_order_id=po.id, po_number=po.po_number, company_name=company_name, status=po.status.value,
        total_amount=po.total_amount, amount_paid=po.amount_paid, created_at=po.created_at,
        items=[
            SupplierOrderItemRead(id=i.id, material_name=material_names.get(i.material_id, "Unknown"), quantity=i.quantity, rate=i.rate, quantity_received=i.quantity_received, amount=i.amount)
            for i in po.items
        ],
    )


def _get_authorized_po(db: Session, marketplace_supplier_id: uuid.UUID, po_id: uuid.UUID) -> tuple[MarketplacePoAttribution, PurchaseOrder, str]:
    row = (
        db.query(MarketplacePoAttribution, PurchaseOrder, Company.name)
        .join(PurchaseOrder, PurchaseOrder.id == MarketplacePoAttribution.purchase_order_id)
        .join(Company, Company.id == MarketplacePoAttribution.company_id)
        .options(selectinload(PurchaseOrder.items))
        .filter(MarketplacePoAttribution.marketplace_supplier_id == marketplace_supplier_id, MarketplacePoAttribution.purchase_order_id == po_id)
        .first()
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return row


def get_order(db: Session, marketplace_supplier_id: uuid.UUID, po_id: uuid.UUID) -> SupplierOrderRead:
    _a, po, company_name = _get_authorized_po(db, marketplace_supplier_id, po_id)
    return _read(po, company_name, db)


def list_delivery_updates(db: Session, marketplace_supplier_id: uuid.UUID, po_id: uuid.UUID) -> list[SupplierDeliveryUpdateRead]:
    _get_authorized_po(db, marketplace_supplier_id, po_id)  # authorization
    rows = db.query(MarketplaceDeliveryReport).filter(MarketplaceDeliveryReport.purchase_order_id == po_id).order_by(MarketplaceDeliveryReport.created_at.desc()).all()
    return [SupplierDeliveryUpdateRead.model_validate(r) for r in rows]


def submit_delivery_update(db: Session, marketplace_supplier_id: uuid.UUID, supplier_user_id: uuid.UUID, po_id: uuid.UUID, payload: SupplierDeliveryUpdateCreate) -> SupplierDeliveryUpdateRead:
    attribution, _po, _company_name = _get_authorized_po(db, marketplace_supplier_id, po_id)

    existing = (
        db.query(MarketplaceDeliveryReport)
        .filter(MarketplaceDeliveryReport.purchase_order_id == po_id, MarketplaceDeliveryReport.external_reference == payload.external_reference)
        .first()
    )
    if existing:
        return SupplierDeliveryUpdateRead(**SupplierDeliveryUpdateRead.model_validate(existing).model_dump(exclude={"already_recorded"}), already_recorded=True)

    report = MarketplaceDeliveryReport(
        company_id=attribution.company_id, purchase_order_id=po_id, external_reference=payload.external_reference,
        note=payload.note, reported_by_supplier_user_id=supplier_user_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return SupplierDeliveryUpdateRead(**SupplierDeliveryUpdateRead.model_validate(report).model_dump(exclude={"already_recorded"}), already_recorded=False)
