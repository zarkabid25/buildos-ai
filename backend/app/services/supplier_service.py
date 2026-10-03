import uuid

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.updates import apply_changes
from app.models.enums import PurchaseOrderStatus
from app.models.procurement import GoodsReceipt, PurchaseOrder
from app.models.project import Project
from app.models.supplier import Supplier, SupplierContact
from app.schemas.supplier import (
    SupplierContactCreate,
    SupplierCreate,
    SupplierPerformance,
    SupplierTransaction,
    SupplierUpdate,
)

# A PO counts as a commitment to the supplier once it's approved.
_COMMITTED = (
    PurchaseOrderStatus.APPROVED,
    PurchaseOrderStatus.PARTIALLY_RECEIVED,
    PurchaseOrderStatus.RECEIVED,
)


def list_suppliers(db: Session, company_id: uuid.UUID) -> list[Supplier]:
    return (
        db.query(Supplier)
        .filter(Supplier.company_id == company_id)
        .order_by(Supplier.name.asc())
        .all()
    )


def get_supplier(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
    supplier = (
        db.query(Supplier)
        .filter(Supplier.company_id == company_id, Supplier.id == supplier_id)
        .first()
    )
    if not supplier:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


def create_supplier(db: Session, company_id: uuid.UUID, payload: SupplierCreate) -> Supplier:
    supplier = Supplier(company_id=company_id, **payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(
    db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierUpdate
) -> Supplier:
    supplier = get_supplier(db, company_id, supplier_id)
    apply_changes(supplier, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    supplier = get_supplier(db, company_id, supplier_id)
    db.delete(supplier)
    db.commit()


def list_contacts(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> list[SupplierContact]:
    get_supplier(db, company_id, supplier_id)
    return (
        db.query(SupplierContact)
        .filter(SupplierContact.company_id == company_id, SupplierContact.supplier_id == supplier_id)
        .order_by(SupplierContact.name.asc())
        .all()
    )


def add_contact(
    db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierContactCreate
) -> SupplierContact:
    get_supplier(db, company_id, supplier_id)
    contact = SupplierContact(company_id=company_id, supplier_id=supplier_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def remove_contact(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    contact = (
        db.query(SupplierContact)
        .filter(
            SupplierContact.id == contact_id,
            SupplierContact.supplier_id == supplier_id,
            SupplierContact.company_id == company_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier contact not found")
    db.delete(contact)
    db.commit()


def list_transactions(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> list[SupplierTransaction]:
    """Every PO placed with this supplier, newest first, with ordered vs received value."""
    get_supplier(db, company_id, supplier_id)
    pos = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.supplier_id == supplier_id)
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )
    po_ids = [po.id for po in pos]
    receipts = {}
    project_names = {}
    if po_ids:
        receipts = {
            po_id: (count, last)
            for po_id, count, last in db.query(
                GoodsReceipt.purchase_order_id, func.count(GoodsReceipt.id), func.max(GoodsReceipt.created_at)
            )
            .filter(GoodsReceipt.company_id == company_id, GoodsReceipt.purchase_order_id.in_(po_ids))
            .group_by(GoodsReceipt.purchase_order_id)
        }
        project_ids = {po.project_id for po in pos if po.project_id}
        if project_ids:
            project_names = dict(
                db.query(Project.id, Project.name).filter(Project.company_id == company_id, Project.id.in_(project_ids))
            )

    return [
        SupplierTransaction(
            purchase_order_id=po.id,
            po_number=po.po_number,
            project_id=po.project_id,
            project_name=project_names.get(po.project_id),
            status=po.status,
            created_at=po.created_at,
            ordered_amount=po.total_amount,
            received_amount=sum((i.quantity_received * i.rate for i in po.items), Decimal("0")),
            receipt_count=receipts.get(po.id, (0, None))[0],
            last_received_at=receipts.get(po.id, (0, None))[1],
        )
        for po in pos
    ]


def get_performance(db: Session, company_id: uuid.UUID, supplier_id: uuid.UUID) -> SupplierPerformance:
    get_supplier(db, company_id, supplier_id)
    pos = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.supplier_id == supplier_id)
        .all()
    )
    committed = [po for po in pos if po.status in _COMMITTED]
    committed_amount = sum((po.total_amount for po in committed), Decimal("0"))
    received_amount = sum(
        (i.quantity_received * i.rate for po in committed for i in po.items), Decimal("0")
    )

    first_receipts: list = []
    if pos:
        first_receipts = (
            db.query(GoodsReceipt.purchase_order_id, func.min(GoodsReceipt.created_at))
            .filter(GoodsReceipt.company_id == company_id, GoodsReceipt.purchase_order_id.in_([p.id for p in pos]))
            .group_by(GoodsReceipt.purchase_order_id)
            .all()
        )
    created = {po.id: po.created_at for po in pos}
    lead_days = [(first - created[po_id]).total_seconds() / 86400 for po_id, first in first_receipts]

    return SupplierPerformance(
        po_count=len(pos),
        committed_po_count=len(committed),
        fully_received_count=sum(1 for po in pos if po.status == PurchaseOrderStatus.RECEIVED),
        cancelled_count=sum(1 for po in pos if po.status == PurchaseOrderStatus.CANCELLED),
        committed_amount=committed_amount,
        received_amount=received_amount,
        fulfilment_percent=(
            (received_amount / committed_amount * 100).quantize(Decimal("0.1")) if committed_amount else None
        ),
        average_lead_time_days=(
            Decimal(str(sum(lead_days) / len(lead_days))).quantize(Decimal("0.1")) if lead_days else None
        ),
    )
