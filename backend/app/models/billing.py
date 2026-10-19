import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.schema import Index

from app.db.base_class import TimestampedBase
from app.models.enums import BillingPeriod, InvoiceStatus, PaymentSubmissionStatus, SubscriptionStatus


class SubscriptionPlan(TimestampedBase):
    """A SaaS plan (PLAT-028). Limits are plain typed columns -- the known,
    named ones the spec lists -- plus a free-form `features` JSON for anything
    else configurable later without a migration. Never hardcoded in the
    frontend: every screen reads these from the API."""

    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trial_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_projects: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = unlimited
    max_team_members: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_monthly_messages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marketplace_included: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    prices: Mapped[list["PlanPrice"]] = relationship(order_by="PlanPrice.created_at.desc()")


class PlanPrice(TimestampedBase):
    """Versioned (PLAT-028): editing a plan's price never changes what an
    existing invoice says it charged. Exactly one row per (plan, currency,
    billing_period) may have is_current=True at a time, enforced by the
    partial unique index below; superseding a price flips the old row's
    is_current off and inserts a new one, rather than mutating history."""

    __tablename__ = "plan_prices"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod, native_enum=False, length=10, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index(
            "uq_one_current_price_per_plan_currency_period",
            "plan_id", "currency", "billing_period",
            unique=True,
            postgresql_where=text("is_current = true"),
            sqlite_where=text("is_current = 1"),
        ),
    )


class CompanySubscription(TimestampedBase):
    """One company's subscription (PLAT-029). The partial unique index is the
    real concurrency guard against two "live" subscriptions existing at once
    for the same company -- a second concurrent attempt to create one hits a
    database IntegrityError, not just a check that could race."""

    __tablename__ = "company_subscriptions"
    __table_args__ = (
        Index(
            "uq_one_live_subscription_per_company",
            "company_id",
            unique=True,
            postgresql_where=text(
                "status IN ('trialing', 'active', 'pending_payment', 'grace_period')"
            ),
            sqlite_where=text(
                "status IN ('trialing', 'active', 'pending_payment', 'grace_period')"
            ),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=False)
    plan_price_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("plan_prices.id"), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=SubscriptionStatus.TRIALING,
        index=True,
        nullable=False,
    )
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod, native_enum=False, length=10, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    plan: Mapped["SubscriptionPlan"] = relationship()


class SubscriptionInvoice(TimestampedBase):
    __tablename__ = "subscription_invoices"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_subscriptions.id"), index=True, nullable=False)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, native_enum=False, length=10, values_callable=lambda e: [x.value for x in e]),
        default=InvoiceStatus.PENDING,
        index=True,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    billing_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    billing_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["InvoiceLineItem"]] = relationship(cascade="all, delete-orphan")
    payments: Mapped[list["PaymentSubmission"]] = relationship(order_by="PaymentSubmission.created_at.desc()")


class InvoiceLineItem(TimestampedBase):
    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_invoices.id"), index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)


class PaymentSubmission(TimestampedBase):
    """A manual bank-transfer payment claim against one invoice, with a proof
    file (private storage, same backend/validation as every other upload in
    this app). Only platform owner/admin staff may verify or reject --
    support is deliberately excluded, same tier as every other mutating
    platform action in this project. Verifying twice is refused (PENDING is
    the only state verify/reject can act on)."""

    __tablename__ = "payment_submissions"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_invoices.id"), index=True, nullable=False)
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(30), default="bank_transfer", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    proof_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    proof_content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    proof_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PaymentSubmissionStatus] = mapped_column(
        Enum(PaymentSubmissionStatus, native_enum=False, length=10, values_callable=lambda e: [x.value for x in e]),
        default=PaymentSubmissionStatus.PENDING,
        index=True,
        nullable=False,
    )
    verified_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SubscriptionEvent(TimestampedBase):
    """Append-only lifecycle history (PLAT-029/031): every status transition,
    plan change, and payment outcome, for the company's and platform staff's
    own activity screens. Mirrors the AuditLog/PlatformAuditLog convention
    already used everywhere else -- insert only, never updated or deleted."""

    __tablename__ = "subscription_events"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_subscriptions.id"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    actor_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class CompanyLegacyEntitlement(TimestampedBase):
    """Explicit grandfathering record (PLAT-032), one row per company that
    existed before Phase 5 -- inserted by migration 0028 itself, not inferred
    at request time. A legacy company is never auto-charged or restricted:
    entitlement_service treats having this row (and no live subscription) as
    "unlimited, same access as always." Platform staff can review and revoke
    it explicitly (revoked_at), at which point the company would need a real
    subscription like any new one."""

    __tablename__ = "company_legacy_entitlements"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), unique=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    granted_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
