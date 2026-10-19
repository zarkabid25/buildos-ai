"""Marketplace commission attribution and ledger (PLAT-034).

This phase's own mandatory inspection (see docs/daily-log.md Phase 6 entry)
found that a SupplierPayment cannot be reliably traced back to a marketplace
quotation/invitation after the fact: PurchaseOrder has no rfq_id/quotation_id
column, Rfq.awarded_quotation_id isn't even a real foreign key, and
SupplierPayment only knows its purchase_order_id. Chasing that chain
retroactively would be fragile and ambiguous (multiple suppliers can quote on
one RFQ).

The fix applied here is a new, explicit, durable row -- MarketplacePoAttribution
-- written once, at the moment rfq_service.award() actually drafts the PO,
if and only if the awarded quotation already carries a
MarketplaceQuotationAttribution row (Phase 4.1). That single row is the only
thing that ever decides "is this PO commission-eligible"; nothing here
re-derives it from Rfq/Quotation relationships later. Both hooks into
existing ERP code are one additive function call each (see
record_po_attribution_if_marketplace_sourced, called from rfq_service.award,
and accrue_on_supplier_payment, called from payment_service.record_supplier_payment)
-- neither existing function's own logic, calculations, or lifecycle rules
are touched.

Commission accrues on ACTUAL PAYMENT (ON_PAYMENT is the only earning trigger
wired up), never on raw PO value or a goods-receipt event -- a goods receipt
is explicitly not proof of payment anywhere else in this app either
(see MarketplaceDeliveryReport's own docstring), and inventing a synthetic
"payment happened" signal from it would contradict rule #4/#12 of this
project's own architecture (AI/automation never silently executes financial
transactions; the same discipline applies here: only a real, already-posted
SupplierPayment row can trigger commission)."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.commission import CommissionLedgerEntry, MarketplacePoAttribution, SupplierCommissionAgreement
from app.models.enums import CommissionBasis, CommissionLedgerEntryKind
from app.models.marketplace_supplier import MarketplaceQuotationAttribution
from app.models.payment import SupplierPayment
from app.models.platform_admin import PlatformAdmin
from app.schemas.commission import CommissionLedgerEntryRead
from app.services import commission_agreement_service


def record_po_attribution_if_marketplace_sourced(
    db: Session, company_id: uuid.UUID, purchase_order_id: uuid.UUID, rfq_id: uuid.UUID, quotation_id: uuid.UUID, total_amount: Decimal
) -> MarketplacePoAttribution | None:
    """Called from rfq_service.award() in the same transaction that drafts
    the PO. A no-op (returns None) for the overwhelming majority of POs --
    ordinary ERP purchase orders, awarded from a non-marketplace quotation --
    which is exactly what keeps commission from ever touching them."""
    attribution_src = db.query(MarketplaceQuotationAttribution).filter(MarketplaceQuotationAttribution.quotation_id == quotation_id).first()
    if not attribution_src:
        return None
    attribution = MarketplacePoAttribution(
        company_id=company_id,
        purchase_order_id=purchase_order_id,
        rfq_id=rfq_id,
        quotation_id=quotation_id,
        marketplace_supplier_id=attribution_src.marketplace_supplier_id,
        attributed_amount=total_amount,
    )
    db.add(attribution)
    db.flush()
    return attribution


def get_po_attribution(db: Session, purchase_order_id: uuid.UUID) -> MarketplacePoAttribution | None:
    return db.query(MarketplacePoAttribution).filter(MarketplacePoAttribution.purchase_order_id == purchase_order_id).first()


def to_read(entry: CommissionLedgerEntry, supplier_name: str | None = None) -> CommissionLedgerEntryRead:
    return CommissionLedgerEntryRead(
        id=entry.id, company_id=entry.company_id, purchase_order_id=entry.purchase_order_id,
        marketplace_supplier_id=entry.marketplace_supplier_id, marketplace_supplier_name=supplier_name,
        supplier_payment_id=entry.supplier_payment_id, kind=entry.kind, agreement_id=entry.agreement_id,
        basis_snapshot=entry.basis_snapshot, rate_snapshot=entry.rate_snapshot, fixed_fee_snapshot=entry.fixed_fee_snapshot,
        base_amount=entry.base_amount, commission_amount=entry.commission_amount, related_entry_id=entry.related_entry_id,
        invoiced=entry.invoiced, note=entry.note, created_at=entry.created_at,
    )


def accrue_on_supplier_payment(db: Session, company_id: uuid.UUID, payment: SupplierPayment) -> CommissionLedgerEntry | None:
    """Called from payment_service.record_supplier_payment(), right after a
    real SupplierPayment row is flushed, in the same transaction. Returns
    None (no commission) whenever: the PO isn't marketplace-attributed, no
    agreement is currently in force for that supplier as of the payment
    date, or (fixed-fee basis only) the fee already accrued on an earlier
    payment against this same PO. The partial unique index on
    commission_ledger_entries.supplier_payment_id is the real guard against
    a retried/duplicated payment ever accruing commission twice -- this
    function relies on that DB constraint, not just this in-memory check."""
    attribution = get_po_attribution(db, payment.purchase_order_id)
    if not attribution:
        return None

    agreement = commission_agreement_service.get_active_agreement_for_date(db, attribution.marketplace_supplier_id, payment.paid_on)
    if not agreement:
        return None

    if agreement.basis == CommissionBasis.FIXED_FEE:
        already_charged = (
            db.query(CommissionLedgerEntry)
            .filter(
                CommissionLedgerEntry.purchase_order_id == payment.purchase_order_id,
                CommissionLedgerEntry.kind == CommissionLedgerEntryKind.ACCRUAL,
                CommissionLedgerEntry.agreement_id == agreement.id,
            )
            .first()
        )
        if already_charged:
            return None
        commission_amount = agreement.fixed_fee_amount
    else:
        commission_amount = (payment.amount * agreement.rate).quantize(Decimal("0.01"))

    entry = CommissionLedgerEntry(
        company_id=company_id,
        purchase_order_id=payment.purchase_order_id,
        marketplace_supplier_id=attribution.marketplace_supplier_id,
        supplier_payment_id=payment.id,
        kind=CommissionLedgerEntryKind.ACCRUAL,
        agreement_id=agreement.id,
        basis_snapshot=agreement.basis,
        rate_snapshot=agreement.rate,
        fixed_fee_snapshot=agreement.fixed_fee_amount,
        base_amount=payment.amount,
        commission_amount=commission_amount,
    )
    db.add(entry)
    try:
        db.flush()
    except IntegrityError:
        # The partial unique index caught a duplicate accrual attempt for
        # this exact payment (a retry, or a race) -- refuse silently rather
        # than double-charging; the caller's own transaction continues.
        db.rollback()
        return None
    return entry


def reverse_entry(db: Session, original_entry_id: uuid.UUID, actor_staff: PlatformAdmin, note: str) -> CommissionLedgerEntry:
    """A full reversal of one ACCRUAL entry -- used by the dispute workflow
    when a dispute is approved. Never edits the original row; posts a new
    REVERSAL entry with the opposite sign."""
    original = db.query(CommissionLedgerEntry).filter(CommissionLedgerEntry.id == original_entry_id).first()
    reversal = CommissionLedgerEntry(
        company_id=original.company_id,
        purchase_order_id=original.purchase_order_id,
        marketplace_supplier_id=original.marketplace_supplier_id,
        kind=CommissionLedgerEntryKind.REVERSAL,
        agreement_id=original.agreement_id,
        basis_snapshot=original.basis_snapshot,
        rate_snapshot=original.rate_snapshot,
        fixed_fee_snapshot=original.fixed_fee_snapshot,
        base_amount=original.base_amount,
        commission_amount=-original.commission_amount,
        related_entry_id=original.id,
        note=note,
        created_by_staff_id=actor_staff.id,
    )
    db.add(reversal)
    db.flush()
    return reversal


def post_adjustment(db: Session, company_id: uuid.UUID, purchase_order_id: uuid.UUID, marketplace_supplier_id: uuid.UUID, amount: Decimal, actor_staff: PlatformAdmin, note: str) -> CommissionLedgerEntry:
    """A standalone, staff-initiated correction -- not tied to a dispute.
    `amount` may be negative (a credit) or positive (an extra charge); it is
    never applied by editing a prior row."""
    entry = CommissionLedgerEntry(
        company_id=company_id,
        purchase_order_id=purchase_order_id,
        marketplace_supplier_id=marketplace_supplier_id,
        kind=CommissionLedgerEntryKind.ADJUSTMENT,
        base_amount=abs(amount),
        commission_amount=amount,
        note=note,
        created_by_staff_id=actor_staff.id,
    )
    db.add(entry)
    db.flush()
    return entry


def list_ledger(
    db: Session, marketplace_supplier_id: uuid.UUID | None = None, purchase_order_id: uuid.UUID | None = None, company_id: uuid.UUID | None = None
) -> list[CommissionLedgerEntryRead]:
    from app.models.marketplace_supplier import MarketplaceSupplier

    query = db.query(CommissionLedgerEntry, MarketplaceSupplier.name).join(MarketplaceSupplier, MarketplaceSupplier.id == CommissionLedgerEntry.marketplace_supplier_id)
    if marketplace_supplier_id:
        query = query.filter(CommissionLedgerEntry.marketplace_supplier_id == marketplace_supplier_id)
    if purchase_order_id:
        query = query.filter(CommissionLedgerEntry.purchase_order_id == purchase_order_id)
    if company_id:
        query = query.filter(CommissionLedgerEntry.company_id == company_id)
    rows = query.order_by(CommissionLedgerEntry.created_at.desc()).all()
    return [to_read(entry, name) for entry, name in rows]


def get_ledger_entry(db: Session, ledger_entry_id: uuid.UUID) -> CommissionLedgerEntry:
    from fastapi import HTTPException, status

    entry = db.query(CommissionLedgerEntry).filter(CommissionLedgerEntry.id == ledger_entry_id).first()
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ledger entry not found")
    return entry


def net_commission_for_supplier(db: Session, marketplace_supplier_id: uuid.UUID) -> Decimal:
    """Sum of every ledger entry (accrual + reversal + adjustment) for one
    supplier -- what that supplier actually, currently owes/has earned
    against, net of every correction ever posted."""
    total = db.query(CommissionLedgerEntry).filter(CommissionLedgerEntry.marketplace_supplier_id == marketplace_supplier_id).all()
    return sum((e.commission_amount for e in total), Decimal("0")).quantize(Decimal("0.01"))
