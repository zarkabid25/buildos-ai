import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    CommissionAgreementStatus,
    CommissionBasis,
    CommissionDisputeStatus,
    CommissionEarningTrigger,
    CommissionInvoiceStatus,
    CommissionLedgerEntryKind,
)


# ---- PLAT-033: supplier commission agreements ----------------------------------------------


class CommissionAgreementCreate(BaseModel):
    basis: CommissionBasis
    rate: Decimal | None = Field(default=None, ge=0, le=1)
    fixed_fee_amount: Decimal | None = Field(default=None, ge=0)
    earning_trigger: CommissionEarningTrigger = CommissionEarningTrigger.ON_PAYMENT
    effective_from: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _basis_matches_fields(self) -> "CommissionAgreementCreate":
        if self.basis == CommissionBasis.PERCENTAGE and self.rate is None:
            raise ValueError("A percentage agreement needs a rate")
        if self.basis == CommissionBasis.FIXED_FEE and self.fixed_fee_amount is None:
            raise ValueError("A fixed-fee agreement needs a fixed_fee_amount")
        return self


class CommissionAgreementRead(BaseModel):
    id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    version: int
    basis: CommissionBasis
    rate: Decimal | None
    fixed_fee_amount: Decimal | None
    earning_trigger: CommissionEarningTrigger
    status: CommissionAgreementStatus
    effective_from: datetime
    effective_to: datetime | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- PLAT-034: commission ledger -----------------------------------------------------------


class CommissionLedgerEntryRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    purchase_order_id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str | None = None
    supplier_payment_id: uuid.UUID | None
    kind: CommissionLedgerEntryKind
    agreement_id: uuid.UUID | None
    basis_snapshot: CommissionBasis | None
    rate_snapshot: Decimal | None
    fixed_fee_snapshot: Decimal | None
    base_amount: Decimal
    commission_amount: Decimal
    related_entry_id: uuid.UUID | None
    invoiced: bool
    note: str | None
    created_at: datetime


class CommissionAdjustmentRequest(BaseModel):
    """A manual, staff-initiated adjustment against a specific PO/supplier --
    distinct from a dispute's reversal, this is used when staff need to add
    or reduce a commission amount outside of the dispute workflow (e.g. a
    one-off correction). Always a new compensating entry, never an edit."""

    purchase_order_id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    amount: Decimal  # may be negative
    note: str = Field(min_length=1, max_length=500)


# ---- PLAT-036: disputes ----------------------------------------------------------------------


class CommissionDisputeCreate(BaseModel):
    ledger_entry_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=1000)


class CommissionDisputeReview(BaseModel):
    approve: bool
    resolution_notes: str = Field(min_length=1, max_length=1000)


class CommissionDisputeRead(BaseModel):
    id: uuid.UUID
    ledger_entry_id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    reason: str
    status: CommissionDisputeStatus
    raised_by_staff_id: uuid.UUID
    raised_by_staff_name: str | None = None
    reviewed_by_staff_id: uuid.UUID | None
    reviewed_by_staff_name: str | None = None
    resolution_notes: str | None
    resulting_entry_id: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime


# ---- PLAT-035: commission invoices and payments ----------------------------------------------


class GenerateCommissionInvoiceRequest(BaseModel):
    marketplace_supplier_id: uuid.UUID
    period_start: date
    period_end: date
    due_date: date


class CommissionInvoiceLineItemRead(BaseModel):
    id: uuid.UUID
    ledger_entry_id: uuid.UUID
    description: str
    amount: Decimal

    model_config = {"from_attributes": True}


class CommissionPaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0)
    paid_on: date
    method: str = Field(default="bank_transfer", max_length=30)
    receipt_reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class CommissionPaymentRead(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    paid_on: date
    method: str
    receipt_reference: str | None
    notes: str | None
    recorded_by_staff_id: uuid.UUID
    recorded_by_staff_name: str | None = None
    created_at: datetime


class CommissionInvoiceRead(BaseModel):
    id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str | None = None
    invoice_number: str
    status: CommissionInvoiceStatus
    currency: str
    subtotal: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    outstanding: Decimal
    period_start: date
    period_end: date
    due_date: date
    items: list[CommissionInvoiceLineItemRead]
    payments: list[CommissionPaymentRead]
    created_at: datetime


# ---- PLAT-037: revenue dashboard --------------------------------------------------------------


class CommissionMonthlyTrendPoint(BaseModel):
    month: str
    amount: Decimal


class SupplierRevenueContribution(BaseModel):
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str
    commission_earned: Decimal


class CommissionRevenueDashboard(BaseModel):
    commission_earned: Decimal  # net accruals (accrual + reversal + adjustment), all-time
    commission_invoiced: Decimal
    commission_collected: Decimal
    outstanding_commission: Decimal
    active_agreements: int
    marketplace_attributed_order_count: int
    marketplace_attributed_order_value: Decimal
    disputed_amount: Decimal  # sum of base_amount on OPEN disputes' original entries
    monthly_trend: list[CommissionMonthlyTrendPoint]
    supplier_contributions: list[SupplierRevenueContribution]
