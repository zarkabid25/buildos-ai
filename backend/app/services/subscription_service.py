"""Subscription lifecycle (PLAT-029). An explicit state machine -- every
transition is checked against _ALLOWED_TRANSITIONS before being applied, and
"at most one live subscription per company" is enforced at the database level
(CompanySubscription's partial unique index), not only here, so a race
between two concurrent requests still can't create a duplicate."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.billing import CompanyLegacyEntitlement, CompanySubscription, SubscriptionEvent
from app.models.company import Company
from app.models.enums import LIVE_SUBSCRIPTION_STATUSES, SubscriptionStatus
from app.models.platform_admin import PlatformAdmin
from app.models.user import User
from app.schemas.billing import CompanyBillingSummaryRead, PlanChangeRequest, SubscriptionCreate, SubscriptionEventRead, SubscriptionRead
from app.core.config import get_settings
from app.services import audit_service, email_service, platform_audit_service, subscription_plan_service

_ALLOWED_TRANSITIONS: dict[SubscriptionStatus, set[SubscriptionStatus]] = {
    SubscriptionStatus.TRIALING: {SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING_PAYMENT, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED},
    SubscriptionStatus.ACTIVE: {SubscriptionStatus.PENDING_PAYMENT, SubscriptionStatus.GRACE_PERIOD, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED},
    SubscriptionStatus.PENDING_PAYMENT: {SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE_PERIOD, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED},
    SubscriptionStatus.GRACE_PERIOD: {SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED},
    SubscriptionStatus.CANCELLED: set(),
    SubscriptionStatus.EXPIRED: set(),
}

GRACE_PERIOD_DAYS = 7


def _read(sub: CompanySubscription) -> SubscriptionRead:
    return SubscriptionRead(
        id=sub.id,
        company_id=sub.company_id,
        plan_id=sub.plan_id,
        plan_name=sub.plan.name,
        status=sub.status,
        billing_period=sub.billing_period,
        trial_ends_at=sub.trial_ends_at,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        grace_period_ends_at=sub.grace_period_ends_at,
        cancelled_at=sub.cancelled_at,
        created_at=sub.created_at,
    )


def get_live_subscription(db: Session, company_id: uuid.UUID) -> CompanySubscription | None:
    return (
        db.query(CompanySubscription)
        .filter(CompanySubscription.company_id == company_id, CompanySubscription.status.in_(LIVE_SUBSCRIPTION_STATUSES))
        .first()
    )


def get_subscription(db: Session, company_id: uuid.UUID, subscription_id: uuid.UUID) -> CompanySubscription:
    sub = db.query(CompanySubscription).filter(CompanySubscription.company_id == company_id, CompanySubscription.id == subscription_id).first()
    if not sub:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    return sub


def list_subscriptions(db: Session, company_id: uuid.UUID) -> list[SubscriptionRead]:
    subs = db.query(CompanySubscription).filter(CompanySubscription.company_id == company_id).order_by(CompanySubscription.created_at.desc()).all()
    return [_read(s) for s in subs]


def get_current_subscription_read(db: Session, company_id: uuid.UUID) -> SubscriptionRead | None:
    sub = get_live_subscription(db, company_id)
    return _read(sub) if sub else None


def _record_event(db: Session, sub: CompanySubscription, event_type: str, from_status: SubscriptionStatus | None, to_status: SubscriptionStatus | None, summary: str, actor_user: User | None = None, actor_staff: PlatformAdmin | None = None) -> None:
    db.add(
        SubscriptionEvent(
            company_id=sub.company_id,
            subscription_id=sub.id,
            event_type=event_type,
            from_status=from_status.value if from_status else None,
            to_status=to_status.value if to_status else None,
            summary=summary,
            actor_user_id=actor_user.id if actor_user else None,
            actor_staff_id=actor_staff.id if actor_staff else None,
        )
    )


def create_subscription(db: Session, company_id: uuid.UUID, actor_user: User, payload: SubscriptionCreate) -> SubscriptionRead:
    plan = subscription_plan_service.get_plan_model(db, payload.plan_id)
    if not plan.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This plan is no longer available")
    price = subscription_plan_service.get_current_price(db, plan.id, payload.currency, payload.billing_period)

    now = datetime.now(timezone.utc)
    trial_ends_at = now + timedelta(days=plan.trial_days) if plan.trial_days > 0 else None
    sub = CompanySubscription(
        company_id=company_id,
        plan_id=plan.id,
        plan_price_id=price.id,
        status=SubscriptionStatus.TRIALING if trial_ends_at else SubscriptionStatus.PENDING_PAYMENT,
        billing_period=payload.billing_period,
        trial_ends_at=trial_ends_at,
        current_period_start=now if not trial_ends_at else None,
    )
    db.add(sub)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # The partial unique index caught a race (or an existing live
        # subscription this check should have already found) -- refuse
        # cleanly rather than leaving two live rows.
        raise HTTPException(status.HTTP_409_CONFLICT, "This company already has an active subscription")

    _record_event(db, sub, "subscription.created", None, sub.status, f"Subscribed to {plan.name}", actor_user=actor_user)
    audit_service.record(db, company_id, actor_user.id, "billing.subscription_created", "company_subscription", sub.id, f"Subscribed to {plan.name}")
    db.commit()
    db.refresh(sub)
    company = db.query(Company).filter(Company.id == company_id).first()
    email_service.send_templated(
        db, "billing_notification", actor_user.email,
        {
            "event": "New subscription started", "company_name": company.name if company else "your company",
            "detail": f"Subscribed to the {plan.name} plan.", "billing_url": f"{get_settings().app_base_url}/billing",
        },
        dedup_key=f"billing-subscription-created:{sub.id}",
    )
    return _read(sub)


def change_plan(db: Session, company_id: uuid.UUID, actor_user: User, subscription_id: uuid.UUID, payload: PlanChangeRequest) -> SubscriptionRead:
    sub = get_subscription(db, company_id, subscription_id)
    if sub.status not in (SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Can't change plan while subscription is {sub.status.value}")
    new_plan = subscription_plan_service.get_plan_model(db, payload.plan_id)
    if not new_plan.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This plan is no longer available")
    period = payload.billing_period or sub.billing_period
    price = subscription_plan_service.get_current_price(db, new_plan.id, sub.plan.prices[0].currency if sub.plan.prices else "USD", period)

    old_plan_name = sub.plan.name
    sub.plan_id = new_plan.id
    sub.plan_price_id = price.id
    sub.billing_period = period
    _record_event(db, sub, "subscription.plan_changed", sub.status, sub.status, f"Changed plan: {old_plan_name} -> {new_plan.name}", actor_user=actor_user)
    audit_service.record(db, company_id, actor_user.id, "billing.plan_changed", "company_subscription", sub.id, f"{old_plan_name} -> {new_plan.name}")
    db.commit()
    db.refresh(sub)
    return _read(sub)


def _transition(db: Session, sub: CompanySubscription, to_status: SubscriptionStatus, event_type: str, summary: str, actor_user: User | None = None, actor_staff: PlatformAdmin | None = None) -> None:
    if to_status not in _ALLOWED_TRANSITIONS.get(sub.status, set()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Can't move a subscription from {sub.status.value} to {to_status.value}")
    from_status = sub.status
    sub.status = to_status
    _record_event(db, sub, event_type, from_status, to_status, summary, actor_user=actor_user, actor_staff=actor_staff)


def cancel_subscription(db: Session, company_id: uuid.UUID, actor_user: User, subscription_id: uuid.UUID) -> SubscriptionRead:
    sub = get_subscription(db, company_id, subscription_id)
    _transition(db, sub, SubscriptionStatus.CANCELLED, "subscription.cancelled", "Cancelled by the company", actor_user=actor_user)
    sub.cancelled_at = datetime.now(timezone.utc)
    audit_service.record(db, company_id, actor_user.id, "billing.subscription_cancelled", "company_subscription", sub.id, "Subscription cancelled")
    db.commit()
    db.refresh(sub)
    return _read(sub)


def activate_subscription(db: Session, company_id: uuid.UUID, subscription_id: uuid.UUID, actor_staff: PlatformAdmin, period_days: int = 30) -> SubscriptionRead:
    """Moves a subscription to ACTIVE with a fresh billing period -- called
    after a payment is verified (PLAT-030), or directly by staff."""
    sub = get_subscription(db, company_id, subscription_id)
    now = datetime.now(timezone.utc)
    _transition(db, sub, SubscriptionStatus.ACTIVE, "subscription.activated", "Activated after payment verification", actor_staff=actor_staff)
    sub.current_period_start = now
    sub.current_period_end = now + timedelta(days=period_days)
    sub.grace_period_ends_at = None
    db.commit()
    db.refresh(sub)
    return _read(sub)


def enter_grace_period(db: Session, company_id: uuid.UUID, subscription_id: uuid.UUID, actor_staff: PlatformAdmin | None = None) -> SubscriptionRead:
    sub = get_subscription(db, company_id, subscription_id)
    _transition(db, sub, SubscriptionStatus.GRACE_PERIOD, "subscription.grace_period_started", f"Grace period started ({GRACE_PERIOD_DAYS} days)", actor_staff=actor_staff)
    sub.grace_period_ends_at = datetime.now(timezone.utc) + timedelta(days=GRACE_PERIOD_DAYS)
    db.commit()
    db.refresh(sub)
    return _read(sub)


def expire_subscription(db: Session, company_id: uuid.UUID, subscription_id: uuid.UUID, actor_staff: PlatformAdmin | None = None) -> SubscriptionRead:
    sub = get_subscription(db, company_id, subscription_id)
    _transition(db, sub, SubscriptionStatus.EXPIRED, "subscription.expired", "Subscription expired", actor_staff=actor_staff)
    db.commit()
    db.refresh(sub)
    return _read(sub)


def record_renewal_invoice_requested(db: Session, sub: CompanySubscription, actor_user: User) -> None:
    """Logged by the company-facing renewal endpoint (app/api/v1/billing.py)
    whenever a renewal invoice is actually generated -- not on a repeated
    request that found an existing pending one, so the history never implies
    more renewal attempts happened than really did."""
    _record_event(db, sub, "subscription.renewal_invoice_requested", sub.status, sub.status, "Renewal invoice generated", actor_user=actor_user)


def _billing_summary(company: Company, sub: CompanySubscription | None, is_legacy: bool) -> CompanyBillingSummaryRead:
    return CompanyBillingSummaryRead(
        company_id=company.id,
        company_name=company.name,
        plan_id=sub.plan_id if sub else None,
        plan_name=sub.plan.name if sub else None,
        status=sub.status.value if sub else ("legacy" if is_legacy else "none"),
        billing_period=sub.billing_period if sub else None,
        trial_ends_at=sub.trial_ends_at if sub else None,
        current_period_end=sub.current_period_end if sub else None,
        grace_period_ends_at=sub.grace_period_ends_at if sub else None,
        is_legacy=is_legacy,
    )


def _latest_subscription_for_company(db: Session, company_id: uuid.UUID) -> CompanySubscription | None:
    sub = get_live_subscription(db, company_id)
    if sub:
        return sub
    # No live subscription -- fall back to the most recent historical one
    # (cancelled/expired), purely for display; it is never treated as live.
    return db.query(CompanySubscription).filter(CompanySubscription.company_id == company_id).order_by(CompanySubscription.created_at.desc()).first()


def get_company_billing_summary(db: Session, company_id: uuid.UUID) -> CompanyBillingSummaryRead:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    is_legacy = (
        db.query(CompanyLegacyEntitlement)
        .filter(CompanyLegacyEntitlement.company_id == company_id, CompanyLegacyEntitlement.revoked_at.is_(None))
        .first()
        is not None
    )
    return _billing_summary(company, _latest_subscription_for_company(db, company_id), is_legacy)


def list_billing_companies(db: Session, search: str | None = None, plan_id: uuid.UUID | None = None, status_filter: str | None = None) -> list[CompanyBillingSummaryRead]:
    """Company directory for the platform-admin billing screens (Task 1).
    Reads existing subscription rows -- no new lifecycle logic. A company
    with no subscription history at all is correctly labelled "legacy" or
    "none", never silently omitted, so staff can see every company."""
    query = db.query(Company)
    if search:
        query = query.filter(Company.name.ilike(f"%{search}%"))
    companies = query.order_by(Company.name.asc()).all()
    legacy_ids = {row[0] for row in db.query(CompanyLegacyEntitlement.company_id).filter(CompanyLegacyEntitlement.revoked_at.is_(None)).all()}

    results: list[CompanyBillingSummaryRead] = []
    for company in companies:
        sub = _latest_subscription_for_company(db, company.id)
        is_legacy = company.id in legacy_ids
        summary = _billing_summary(company, sub, is_legacy)
        if status_filter and summary.status != status_filter:
            continue
        if plan_id and (not sub or sub.plan_id != plan_id):
            continue
        results.append(summary)
    return results


def list_events(db: Session, company_id: uuid.UUID, subscription_id: uuid.UUID | None = None) -> list[SubscriptionEventRead]:
    query = (
        db.query(SubscriptionEvent, PlatformAdmin.full_name, User.full_name)
        .outerjoin(PlatformAdmin, PlatformAdmin.id == SubscriptionEvent.actor_staff_id)
        .outerjoin(User, User.id == SubscriptionEvent.actor_user_id)
        .filter(SubscriptionEvent.company_id == company_id)
    )
    if subscription_id:
        query = query.filter(SubscriptionEvent.subscription_id == subscription_id)
    rows = query.order_by(SubscriptionEvent.created_at.desc()).all()
    return [
        SubscriptionEventRead(id=e.id, event_type=e.event_type, from_status=e.from_status, to_status=e.to_status, summary=e.summary, actor_staff_name=staff_name, actor_user_name=user_name, created_at=e.created_at)
        for e, staff_name, user_name in rows
    ]
