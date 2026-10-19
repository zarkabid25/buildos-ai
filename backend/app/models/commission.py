"""Marketplace commissions (Phase 6, PLAT-033..037) -- BuildOS AI's second
revenue stream, kept entirely independent of SaaS subscription billing
(app/models/billing.py). Companies pay subscriptions; marketplace suppliers
pay commissions under their own commercial agreements. Nothing here changes
how a purchase order, goods receipt, or supplier payment is created or
calculated -- see commission_service.py's docstring for exactly how
commission-eligibility and accrual hook into the existing ERP flows
additively, without rewriting them."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from app.db.base_class import TimestampedBase
from app.models.enums import (
    CommissionAgreementStatus,
    CommissionBasis,
    CommissionDisputeStatus,
    CommissionEarningTrigger,
    CommissionInvoiceStatus,
    CommissionLedgerEntryKind,
)


class SupplierCommissionAgreement(TimestampedBase):
    """A supplier's commercial agreement (PLAT-033). Versioned like
    PlanPrice: editing never happens -- superseding an agreement flips the
    old row's status to SUPERSEDED (with effective_to set) and inserts a new
    ACTIVE row, so a historical commission entry's snapshot always still
    matches the agreement that was actually in force when it accrued. The
    partial unique index below is what "avoid overlapping active agreements
    for the same supplier" actually means at the database level -- scope is
    the whole supplier (this schema doesn't need a finer-grained scope yet)."""

    __tablename__ = "supplier_commission_agreements"
    __table_args__ = (
        Index(
            "uq_one_active_agreement_per_supplier",
            "marketplace_supplier_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    basis: Mapped[CommissionBasis] = mapped_column(Enum(CommissionBasis, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=False)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)  # e.g. 0.0500 = 5%, required when basis=PERCENTAGE
    fixed_fee_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # required when basis=FIXED_FEE
    earning_trigger: Mapped[CommissionEarningTrigger] = mapped_column(
        Enum(CommissionEarningTrigger, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=CommissionEarningTrigger.ON_PAYMENT, nullable=False,
    )
    status: Mapped[CommissionAgreementStatus] = mapped_column(
        Enum(CommissionAgreementStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=CommissionAgreementStatus.ACTIVE, index=True, nullable=False,
    )
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MarketplacePoAttribution(TimestampedBase):
    """The explicit, durable link this phase's own inspection found missing:
    written once, at the moment an RFQ is awarded (rfq_service.award), if
    and only if the awarded quotation already carries a
    MarketplaceQuotationAttribution row. This is the single source of truth
    for "is this purchase order commission-eligible" -- nothing downstream
    ever infers marketplace-origin by chasing Rfq/Quotation relationships
    after the fact. attributed_amount freezes the quotation total at award
    time, for audit purposes; actual commission still accrues off real
    SupplierPayment amounts, not this frozen figure."""

    __tablename__ = "marketplace_po_attributions"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), unique=True, nullable=False)
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfqs.id"), nullable=False)
    quotation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    attributed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class CommissionLedgerEntry(TimestampedBase):
    """Append-only commission ledger (PLAT-034): every accrual, reversal and
    adjustment is its own inserted row, never an edit to a prior one -- same
    philosophy as SubscriptionEvent/AuditLog/SupplierPayment elsewhere in
    this app. An ACCRUAL entry snapshots the agreement terms that produced
    it (basis/rate/fixed_fee), so a later agreement change never silently
    rewrites what a past entry says it charged. The partial unique index on
    supplier_payment_id is the real idempotency guard: a retried or
    duplicated payment event can never accrue commission twice for the same
    SupplierPayment row."""

    __tablename__ = "commission_ledger_entries"
    __table_args__ = (
        Index(
            "uq_one_accrual_per_supplier_payment",
            "supplier_payment_id",
            unique=True,
            postgresql_where=text("kind = 'accrual'"),
            sqlite_where=text("kind = 'accrual'"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), index=True, nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    supplier_payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_payments.id"), nullable=True)
    kind: Mapped[CommissionLedgerEntryKind] = mapped_column(
        Enum(CommissionLedgerEntryKind, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), index=True, nullable=False,
    )
    agreement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_commission_agreements.id"), nullable=True)
    basis_snapshot: Mapped[CommissionBasis | None] = mapped_column(Enum(CommissionBasis, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=True)
    rate_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    fixed_fee_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    base_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # the payment (or disputed) amount this was computed from
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)  # negative for a reversal/negative adjustment
    related_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_ledger_entries.id"), nullable=True)
    invoiced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)


class CommissionDispute(TimestampedBase):
    """A dispute against one ACCRUAL ledger entry (PLAT-036). Approving a
    dispute never edits that entry -- it posts a new REVERSAL
    CommissionLedgerEntry (via commission_service) and records its id here,
    so both what was originally charged and the fact it was reversed stay
    permanently visible."""

    __tablename__ = "commission_disputes"

    ledger_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_ledger_entries.id"), index=True, nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[CommissionDisputeStatus] = mapped_column(
        Enum(CommissionDisputeStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=CommissionDisputeStatus.OPEN, index=True, nullable=False,
    )
    raised_by_staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
    reviewed_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resulting_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_ledger_entries.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommissionInvoice(TimestampedBase):
    """A supplier commission invoice (PLAT-035) -- deliberately a separate
    table from SubscriptionInvoice, never shared, so the two revenue
    streams can never be mixed in one query by accident."""

    __tablename__ = "commission_invoices"

    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[CommissionInvoiceStatus] = mapped_column(
        Enum(CommissionInvoiceStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=CommissionInvoiceStatus.PENDING, index=True, nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)

    items: Mapped[list["CommissionInvoiceLineItem"]] = relationship(cascade="all, delete-orphan")
    payments: Mapped[list["CommissionPayment"]] = relationship(order_by="CommissionPayment.created_at.desc()")


class CommissionInvoiceLineItem(TimestampedBase):
    __tablename__ = "commission_invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_invoices.id"), index=True, nullable=False)
    # Unique (not null) -- the real guard against billing the same ledger entry on two invoices.
    ledger_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_ledger_entries.id"), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class CommissionPayment(TimestampedBase):
    """Manual settlement against a commission invoice (PLAT-035) -- the same
    append-only, PO-level partial-payment ledger pattern as SupplierPayment
    against a PurchaseOrder, just pointed at a CommissionInvoice instead."""

    __tablename__ = "commission_payments"

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("commission_invoices.id"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[str] = mapped_column(String(30), default="bank_transfer", nullable=False)
    receipt_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recorded_by_staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
