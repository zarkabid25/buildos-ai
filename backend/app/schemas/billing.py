import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import BillingPeriod, InvoiceStatus, PaymentSubmissionStatus, SubscriptionStatus


# ---- PLAT-028: plans and versioned prices -----------------------------------------------


class PlanPriceCreate(BaseModel):
    currency: str = Field(min_length=1, max_length=10)
    billing_period: BillingPeriod
    amount: Decimal = Field(gt=0)


class PlanPriceRead(BaseModel):
    id: uuid.UUID
    currency: str
    billing_period: BillingPeriod
    amount: Decimal
    effective_from: datetime
    is_current: bool

    model_config = {"from_attributes": True}


class SubscriptionPlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    trial_days: int = Field(default=0, ge=0)
    max_projects: int | None = Field(default=None, ge=0)
    max_team_members: int | None = Field(default=None, ge=0)
    ai_monthly_messages: int | None = Field(default=None, ge=0)
    storage_gb: int | None = Field(default=None, ge=0)
    marketplace_included: bool = False
    features: dict | None = None
    prices: list[PlanPriceCreate] = Field(default_factory=list)


class SubscriptionPlanUpdate(BaseModel):
    description: str | None = None
    trial_days: int | None = Field(default=None, ge=0)
    max_projects: int | None = Field(default=None, ge=0)
    max_team_members: int | None = Field(default=None, ge=0)
    ai_monthly_messages: int | None = Field(default=None, ge=0)
    storage_gb: int | None = Field(default=None, ge=0)
    marketplace_included: bool | None = None
    features: dict | None = None
    is_active: bool | None = None


class SubscriptionPlanRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    trial_days: int
    max_projects: int | None
    max_team_members: int | None
    ai_monthly_messages: int | None
    storage_gb: int | None
    marketplace_included: bool
    features: dict | None
    is_active: bool
    prices: list[PlanPriceRead]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- PLAT-029: subscription lifecycle ----------------------------------------------------


class SubscriptionCreate(BaseModel):
    plan_id: uuid.UUID
    billing_period: BillingPeriod
    currency: str = Field(default="USD", max_length=10)


class PlanChangeRequest(BaseModel):
    plan_id: uuid.UUID
    billing_period: BillingPeriod | None = None


class SubscriptionRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str
    status: SubscriptionStatus
    billing_period: BillingPeriod
    trial_ends_at: datetime | None
    current_period_start: datetime | None
    current_period_end: datetime | None
    grace_period_ends_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime


class SubscriptionEventRead(BaseModel):
    id: uuid.UUID
    event_type: str
    from_status: str | None
    to_status: str | None
    summary: str
    actor_staff_name: str | None
    actor_user_name: str | None
    created_at: datetime


# ---- PLAT-030: invoices and manual payments -----------------------------------------------


class InvoiceLineItemRead(BaseModel):
    id: uuid.UUID
    description: str
    quantity: int
    unit_price: Decimal
    amount: Decimal

    model_config = {"from_attributes": True}


class PaymentSubmissionRead(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    company_id: uuid.UUID
    submitted_by_user_id: uuid.UUID
    amount: Decimal
    method: str
    reference: str | None
    proof_filename: str
    status: PaymentSubmissionStatus
    verified_by_staff_id: uuid.UUID | None
    verified_by_staff_name: str | None = None
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class InvoiceRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    subscription_id: uuid.UUID
    invoice_number: str
    status: InvoiceStatus
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    billing_period_start: date
    billing_period_end: date
    due_date: date
    paid_at: datetime | None
    items: list[InvoiceLineItemRead]
    payments: list[PaymentSubmissionRead]
    created_at: datetime


class RejectPaymentRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# ---- PLAT-031: entitlements and usage ------------------------------------------------------


class EntitlementRead(BaseModel):
    source: str  # "subscription", "legacy", "none"
    plan_name: str | None
    max_projects: int | None
    max_team_members: int | None
    ai_monthly_messages: int | None
    storage_gb: int | None
    marketplace_included: bool
    current_projects: int
    current_team_members: int
    billing_status: SubscriptionStatus | None
    current_period_end: datetime | None
    grace_period_ends_at: datetime | None


# ---- PLAT-032: legacy entitlement review ---------------------------------------------------


class LegacyEntitlementRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str | None = None
    reason: str
    granted_by_staff_id: uuid.UUID | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
