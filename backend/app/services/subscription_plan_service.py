import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.billing import PlanPrice, SubscriptionPlan
from app.models.enums import BillingPeriod
from app.models.platform_admin import PlatformAdmin
from app.schemas.billing import PlanPriceCreate, SubscriptionPlanCreate, SubscriptionPlanRead, SubscriptionPlanUpdate
from app.services import platform_audit_service


def get_plan_model(db: Session, plan_id: uuid.UUID) -> SubscriptionPlan:
    """Public, unlike most of this module's other internals -- other
    services (subscription_service, entitlement_service) need the real ORM
    object, not just the read schema."""
    plan = (
        db.query(SubscriptionPlan)
        .options(selectinload(SubscriptionPlan.prices))
        .filter(SubscriptionPlan.id == plan_id)
        .first()
    )
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    return plan


def create_plan(db: Session, actor: PlatformAdmin, payload: SubscriptionPlanCreate) -> SubscriptionPlanRead:
    if db.query(SubscriptionPlan).filter(SubscriptionPlan.name == payload.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "A plan with this name already exists")

    plan = SubscriptionPlan(**payload.model_dump(exclude={"prices"}))
    db.add(plan)
    db.flush()
    now = datetime.now(timezone.utc)
    for p in payload.prices:
        db.add(PlanPrice(plan_id=plan.id, currency=p.currency, billing_period=p.billing_period, amount=p.amount, effective_from=now, is_current=True))

    platform_audit_service.record(db, actor.id, "billing.plan_created", "subscription_plan", plan.id, f"Plan {plan.name} created")
    db.commit()
    return SubscriptionPlanRead.model_validate(get_plan_model(db, plan.id))


def list_plans(db: Session, include_inactive: bool = False) -> list[SubscriptionPlanRead]:
    query = db.query(SubscriptionPlan).options(selectinload(SubscriptionPlan.prices))
    if not include_inactive:
        query = query.filter(SubscriptionPlan.is_active.is_(True))
    plans = query.order_by(SubscriptionPlan.created_at.asc()).all()
    return [SubscriptionPlanRead.model_validate(p) for p in plans]


def get_plan(db: Session, plan_id: uuid.UUID) -> SubscriptionPlanRead:
    return SubscriptionPlanRead.model_validate(get_plan_model(db, plan_id))


def update_plan(db: Session, actor: PlatformAdmin, plan_id: uuid.UUID, payload: SubscriptionPlanUpdate) -> SubscriptionPlanRead:
    plan = get_plan_model(db, plan_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    platform_audit_service.record(db, actor.id, "billing.plan_updated", "subscription_plan", plan.id, f"Plan {plan.name} updated")
    db.commit()
    return SubscriptionPlanRead.model_validate(get_plan_model(db, plan_id))


def set_price(db: Session, actor: PlatformAdmin, plan_id: uuid.UUID, payload: PlanPriceCreate) -> SubscriptionPlanRead:
    """Versioned (PLAT-028): supersedes any existing current price for this
    (currency, billing_period) rather than editing it, so past invoices still
    show what they actually charged."""
    plan = get_plan_model(db, plan_id)
    existing_current = (
        db.query(PlanPrice)
        .filter(PlanPrice.plan_id == plan_id, PlanPrice.currency == payload.currency, PlanPrice.billing_period == payload.billing_period, PlanPrice.is_current.is_(True))
        .first()
    )
    if existing_current:
        existing_current.is_current = False
    db.add(PlanPrice(plan_id=plan_id, currency=payload.currency, billing_period=payload.billing_period, amount=payload.amount, effective_from=datetime.now(timezone.utc), is_current=True))
    platform_audit_service.record(
        db, actor.id, "billing.plan_price_updated", "subscription_plan", plan.id,
        f"{plan.name}: new {payload.billing_period.value} price {payload.amount} {payload.currency}",
    )
    db.commit()
    return SubscriptionPlanRead.model_validate(get_plan_model(db, plan_id))


def get_current_price(db: Session, plan_id: uuid.UUID, currency: str, billing_period: BillingPeriod) -> PlanPrice:
    price = (
        db.query(PlanPrice)
        .filter(PlanPrice.plan_id == plan_id, PlanPrice.currency == currency, PlanPrice.billing_period == billing_period, PlanPrice.is_current.is_(True))
        .first()
    )
    if not price:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"No current {billing_period.value} price in {currency} for this plan")
    return price
