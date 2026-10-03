"""Cash in and out (BUILD-054): payments to suppliers against purchase orders, and
receipts from clients for projects. All amounts are plain sums of recorded rows."""

import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.enums import PurchaseOrderStatus
from app.models.payment import ClientReceipt, SupplierPayment
from app.models.procurement import PurchaseOrder
from app.models.project import Project
from app.models.supplier import Supplier
from app.schemas.payment import (
    CashSummary,
    ClientReceiptCreate,
    ClientReceiptRead,
    ProjectCash,
    SupplierPayable,
    SupplierPaymentCreate,
    SupplierPaymentRead,
)
from app.services import audit_service
from app.services.procurement_service import get_purchase_order
from app.services.project_service import get_project

# Money is owed once a PO is approved; draft, pending and cancelled POs can't be paid.
PAYABLE = (PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED, PurchaseOrderStatus.RECEIVED)


def record_supplier_payment(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: SupplierPaymentCreate
) -> SupplierPayment:
    po = get_purchase_order(db, company_id, payload.purchase_order_id)
    if po.status not in PAYABLE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"{po.po_number} is {po.status.value.replace('_', ' ')}; only approved POs can be paid"
        )
    outstanding = (po.total_amount - po.amount_paid).quantize(Decimal("0.01"))
    if payload.amount > outstanding:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"That would overpay {po.po_number}: only {outstanding:,.2f} is outstanding",
        )
    payment = SupplierPayment(company_id=company_id, created_by_id=user_id, **payload.model_dump())
    db.add(payment)
    db.flush()
    audit_service.record(
        db, company_id, user_id, "payment.supplier", "purchase_order", po.id,
        f"Paid {payload.amount:,.2f} against {po.po_number} ({payload.method.value.replace('_', ' ')})",
        {"payment_id": str(payment.id), "amount": str(payload.amount), "paid_on": str(payload.paid_on)},
    )
    db.commit()
    db.refresh(payment)
    return payment


def record_client_receipt(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: ClientReceiptCreate
) -> ClientReceipt:
    project = get_project(db, company_id, payload.project_id)
    receipt = ClientReceipt(company_id=company_id, created_by_id=user_id, **payload.model_dump())
    db.add(receipt)
    db.flush()
    audit_service.record(
        db, company_id, user_id, "payment.client_receipt", "project", project.id,
        f"Received {payload.amount:,.2f} for {project.name} ({payload.method.value.replace('_', ' ')})",
        {"receipt_id": str(receipt.id), "amount": str(payload.amount), "received_on": str(payload.received_on)},
    )
    db.commit()
    db.refresh(receipt)
    return receipt


def list_supplier_payments(
    db: Session, company_id: uuid.UUID, purchase_order_id: uuid.UUID | None = None
) -> list[SupplierPaymentRead]:
    query = (
        db.query(SupplierPayment, PurchaseOrder.po_number, Supplier.name)
        .join(PurchaseOrder, (PurchaseOrder.id == SupplierPayment.purchase_order_id) & (PurchaseOrder.company_id == company_id))
        .join(Supplier, Supplier.id == PurchaseOrder.supplier_id)
        .filter(SupplierPayment.company_id == company_id)
    )
    if purchase_order_id:
        query = query.filter(SupplierPayment.purchase_order_id == purchase_order_id)
    rows = query.order_by(SupplierPayment.paid_on.desc(), SupplierPayment.created_at.desc()).all()
    return [
        SupplierPaymentRead.model_validate(p).model_copy(update={"po_number": po_number, "supplier_name": supplier})
        for p, po_number, supplier in rows
    ]


def list_client_receipts(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[ClientReceiptRead]:
    query = (
        db.query(ClientReceipt, Project.name)
        .join(Project, (Project.id == ClientReceipt.project_id) & (Project.company_id == company_id))
        .filter(ClientReceipt.company_id == company_id)
    )
    if project_id:
        query = query.filter(ClientReceipt.project_id == project_id)
    rows = query.order_by(ClientReceipt.received_on.desc(), ClientReceipt.created_at.desc()).all()
    return [ClientReceiptRead.model_validate(r).model_copy(update={"project_name": name}) for r, name in rows]


def cash_summary(db: Session, company_id: uuid.UUID) -> CashSummary:
    projects = {p.id: p.name for p in db.query(Project).filter(Project.company_id == company_id)}
    received: dict[uuid.UUID | None, Decimal] = defaultdict(lambda: Decimal("0"))
    paid_out: dict[uuid.UUID | None, Decimal] = defaultdict(lambda: Decimal("0"))

    for r in db.query(ClientReceipt).filter(ClientReceipt.company_id == company_id):
        received[r.project_id] += r.amount

    pos = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.status.in_(PAYABLE))
        .all()
    )
    payables: dict[uuid.UUID, dict[str, Decimal]] = defaultdict(lambda: {"committed": Decimal("0"), "paid": Decimal("0")})
    for po in pos:
        paid = po.amount_paid
        paid_out[po.project_id] += paid
        payables[po.supplier_id]["committed"] += po.total_amount
        payables[po.supplier_id]["paid"] += paid

    supplier_names = dict(
        db.query(Supplier.id, Supplier.name).filter(Supplier.company_id == company_id, Supplier.id.in_(payables))
    ) if payables else {}

    project_rows = [
        ProjectCash(
            project_id=pid,
            project_name=projects.get(pid, "Not tied to a project") if pid else "Not tied to a project",
            received=received[pid],
            paid_out=paid_out[pid],
            net=received[pid] - paid_out[pid],
        )
        for pid in sorted(set(received) | set(paid_out), key=lambda p: projects.get(p, "~") if p else "~~")
    ]
    payable_rows = sorted(
        (
            SupplierPayable(
                supplier_id=sid,
                supplier_name=supplier_names.get(sid, "Unknown supplier"),
                committed=v["committed"].quantize(Decimal("0.01")),
                paid=v["paid"],
                outstanding=(v["committed"] - v["paid"]).quantize(Decimal("0.01")),
            )
            for sid, v in payables.items()
        ),
        key=lambda p: p.outstanding,
        reverse=True,
    )
    total_received = sum(received.values(), Decimal("0"))
    total_paid = sum(paid_out.values(), Decimal("0"))
    return CashSummary(
        total_received=total_received,
        total_paid_out=total_paid,
        net=total_received - total_paid,
        total_outstanding=sum((p.outstanding for p in payable_rows), Decimal("0")),
        projects=project_rows,
        payables=payable_rows,
    )
