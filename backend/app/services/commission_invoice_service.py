"""Commission invoices and manual settlement (PLAT-035) -- a deliberately
separate table and numbering sequence from SubscriptionInvoice (billing.py),
so the two revenue streams (SaaS subscriptions vs. marketplace commissions)
can never be summed or displayed together by accident."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.commission import CommissionInvoice, CommissionInvoiceLineItem, CommissionLedgerEntry, CommissionPayment
from app.models.enums import CommissionInvoiceStatus, CommissionLedgerEntryKind
from app.models.platform_admin import PlatformAdmin
from app.schemas.commission import CommissionInvoiceRead, CommissionPaymentCreate, CommissionPaymentRead
from app.services import platform_audit_service


def _next_invoice_number(db: Session) -> str:
    count = db.query(CommissionInvoice).count()
    return f"COMM-{10000 + count + 1}"


def _amount_paid(invoice: CommissionInvoice) -> Decimal:
    return sum((p.amount for p in invoice.payments), Decimal("0")).quantize(Decimal("0.01"))


def _read(invoice: CommissionInvoice, supplier_name: str | None, staff_names: dict[uuid.UUID, str] | None = None) -> CommissionInvoiceRead:
    staff_names = staff_names or {}
    paid = _amount_paid(invoice)
    return CommissionInvoiceRead(
        id=invoice.id, marketplace_supplier_id=invoice.marketplace_supplier_id, marketplace_supplier_name=supplier_name,
        invoice_number=invoice.invoice_number, status=invoice.status, currency=invoice.currency,
        subtotal=invoice.subtotal, total_amount=invoice.total_amount, amount_paid=paid,
        outstanding=(invoice.total_amount - paid).quantize(Decimal("0.01")),
        period_start=invoice.period_start, period_end=invoice.period_end, due_date=invoice.due_date,
        items=[{"id": i.id, "ledger_entry_id": i.ledger_entry_id, "description": i.description, "amount": i.amount} for i in invoice.items],
        payments=[
            CommissionPaymentRead(
                id=p.id, invoice_id=p.invoice_id, amount=p.amount, paid_on=p.paid_on, method=p.method,
                receipt_reference=p.receipt_reference, notes=p.notes, recorded_by_staff_id=p.recorded_by_staff_id,
                recorded_by_staff_name=staff_names.get(p.recorded_by_staff_id), created_at=p.created_at,
            )
            for p in invoice.payments
        ],
        created_at=invoice.created_at,
    )


def generate_invoice(db: Session, actor: PlatformAdmin, marketplace_supplier_id: uuid.UUID, period_start: date, period_end: date, due_date: date) -> CommissionInvoiceRead:
    """Bills every ledger entry for this supplier in [period_start,
    period_end) that hasn't already been invoiced. The partial/unique
    constraint on CommissionInvoiceLineItem.ledger_entry_id is the real
    guard against double-billing the same entry on two invoices; `invoiced`
    is set here too so a second call in the same window simply has nothing
    left to bill, rather than relying on the DB constraint to notice."""
    entries = (
        db.query(CommissionLedgerEntry)
        .filter(
            CommissionLedgerEntry.marketplace_supplier_id == marketplace_supplier_id,
            CommissionLedgerEntry.invoiced.is_(False),
            CommissionLedgerEntry.created_at >= period_start,
            CommissionLedgerEntry.created_at < period_end,
        )
        .order_by(CommissionLedgerEntry.created_at.asc())
        .all()
    )
    if not entries:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No unbilled commission entries in this period")

    subtotal = sum((e.commission_amount for e in entries), Decimal("0")).quantize(Decimal("0.01"))
    invoice = CommissionInvoice(
        marketplace_supplier_id=marketplace_supplier_id,
        invoice_number=_next_invoice_number(db),
        status=CommissionInvoiceStatus.PENDING,
        currency="USD",
        subtotal=subtotal,
        total_amount=subtotal,
        period_start=period_start,
        period_end=period_end,
        due_date=due_date,
        created_by_staff_id=actor.id,
    )
    db.add(invoice)
    db.flush()
    for e in entries:
        kind_label = {"accrual": "Commission", "reversal": "Reversal", "adjustment": "Adjustment"}[e.kind.value]
        db.add(CommissionInvoiceLineItem(invoice_id=invoice.id, ledger_entry_id=e.id, description=f"{kind_label} on PO {e.purchase_order_id}", amount=e.commission_amount))
        e.invoiced = True

    platform_audit_service.record(db, actor.id, "commission.invoice_generated", "commission_invoice", invoice.id, f"{invoice.invoice_number}: {len(entries)} entries, {subtotal} {invoice.currency}")
    db.commit()
    return get_invoice(db, invoice.id)


def _get(db: Session, invoice_id: uuid.UUID) -> CommissionInvoice:
    invoice = db.query(CommissionInvoice).options(selectinload(CommissionInvoice.items), selectinload(CommissionInvoice.payments)).filter(CommissionInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Commission invoice not found")
    return invoice


def _supplier_name(db: Session, marketplace_supplier_id: uuid.UUID) -> str | None:
    from app.models.marketplace_supplier import MarketplaceSupplier

    return db.query(MarketplaceSupplier.name).filter(MarketplaceSupplier.id == marketplace_supplier_id).scalar()


def _staff_names(db: Session, invoice: CommissionInvoice) -> dict[uuid.UUID, str]:
    ids = [p.recorded_by_staff_id for p in invoice.payments]
    if not ids:
        return {}
    return dict(db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(ids)).all())


def get_invoice(db: Session, invoice_id: uuid.UUID) -> CommissionInvoiceRead:
    invoice = _get(db, invoice_id)
    return _read(invoice, _supplier_name(db, invoice.marketplace_supplier_id), _staff_names(db, invoice))


def list_invoices(db: Session, marketplace_supplier_id: uuid.UUID | None = None, status_filter: CommissionInvoiceStatus | None = None) -> list[CommissionInvoiceRead]:
    from app.models.marketplace_supplier import MarketplaceSupplier

    query = (
        db.query(CommissionInvoice, MarketplaceSupplier.name)
        .join(MarketplaceSupplier, MarketplaceSupplier.id == CommissionInvoice.marketplace_supplier_id)
        .options(selectinload(CommissionInvoice.items), selectinload(CommissionInvoice.payments))
    )
    if marketplace_supplier_id:
        query = query.filter(CommissionInvoice.marketplace_supplier_id == marketplace_supplier_id)
    if status_filter:
        query = query.filter(CommissionInvoice.status == status_filter)
    rows = query.order_by(CommissionInvoice.created_at.desc()).all()
    return [_read(inv, name, _staff_names(db, inv)) for inv, name in rows]


def record_payment(db: Session, actor: PlatformAdmin, invoice_id: uuid.UUID, payload: CommissionPaymentCreate) -> CommissionInvoiceRead:
    invoice = _get(db, invoice_id)
    if invoice.status in (CommissionInvoiceStatus.PAID, CommissionInvoiceStatus.VOID):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This invoice is {invoice.status.value}; no further payment can be recorded")
    outstanding = (invoice.total_amount - _amount_paid(invoice)).quantize(Decimal("0.01"))
    if payload.amount > outstanding:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"That would overpay this invoice: only {outstanding:,.2f} is outstanding")

    payment = CommissionPayment(invoice_id=invoice.id, recorded_by_staff_id=actor.id, **payload.model_dump())
    db.add(payment)
    db.flush()

    new_total_paid = _amount_paid(invoice) + payload.amount
    invoice.status = CommissionInvoiceStatus.PAID if new_total_paid >= invoice.total_amount else CommissionInvoiceStatus.PARTIALLY_PAID

    platform_audit_service.record(db, actor.id, "commission.payment_recorded", "commission_invoice", invoice.id, f"Recorded {payload.amount} {invoice.currency} against {invoice.invoice_number}")
    db.commit()
    return get_invoice(db, invoice.id)
