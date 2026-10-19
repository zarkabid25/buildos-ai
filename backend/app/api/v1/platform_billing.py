import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.db.session import get_db
from app.models.billing import CompanyLegacyEntitlement, CompanySubscription, SubscriptionInvoice
from app.models.company import Company
from app.models.enums import InvoiceStatus, PlatformStaffRole
from app.models.platform_admin import PlatformAdmin
from app.schemas.billing import (
    InvoiceRead,
    LegacyEntitlementRead,
    PaymentSubmissionRead,
    PlanPriceCreate,
    RejectPaymentRequest,
    SubscriptionEventRead,
    SubscriptionPlanCreate,
    SubscriptionPlanRead,
    SubscriptionPlanUpdate,
    SubscriptionRead,
)
from app.services import invoice_service, platform_audit_service, subscription_plan_service, subscription_service

router = APIRouter(prefix="/platform/billing", tags=["platform-billing"])

# Same tier as every other mutating platform action in this project (company
# approval, marketplace verification, CRM edits): support can view, not mutate.
_can_edit = require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)


# ---- PLAT-028: plans -----------------------------------------------------------------------


@router.post("/plans", response_model=SubscriptionPlanRead, status_code=201)
def create_plan(payload: SubscriptionPlanCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SubscriptionPlanRead:
    return subscription_plan_service.create_plan(db, admin, payload)


@router.get("/plans", response_model=list[SubscriptionPlanRead])
def list_plans(include_inactive: bool = False, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SubscriptionPlanRead]:
    return subscription_plan_service.list_plans(db, include_inactive)


@router.get("/plans/{plan_id}", response_model=SubscriptionPlanRead)
def get_plan(plan_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> SubscriptionPlanRead:
    return subscription_plan_service.get_plan(db, plan_id)


@router.patch("/plans/{plan_id}", response_model=SubscriptionPlanRead)
def update_plan(plan_id: uuid.UUID, payload: SubscriptionPlanUpdate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SubscriptionPlanRead:
    return subscription_plan_service.update_plan(db, admin, plan_id, payload)


@router.post("/plans/{plan_id}/prices", response_model=SubscriptionPlanRead, status_code=201)
def set_price(plan_id: uuid.UUID, payload: PlanPriceCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SubscriptionPlanRead:
    return subscription_plan_service.set_price(db, admin, plan_id, payload)


# ---- PLAT-029: subscriptions, viewed/managed by staff ---------------------------------------


@router.get("/companies/{company_id}/subscriptions", response_model=list[SubscriptionRead])
def list_company_subscriptions(company_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SubscriptionRead]:
    return subscription_service.list_subscriptions(db, company_id)


@router.post("/companies/{company_id}/subscriptions/{subscription_id}/grace-period", response_model=SubscriptionRead)
def enter_grace_period(company_id: uuid.UUID, subscription_id: uuid.UUID, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SubscriptionRead:
    return subscription_service.enter_grace_period(db, company_id, subscription_id, actor_staff=admin)


@router.post("/companies/{company_id}/subscriptions/{subscription_id}/expire", response_model=SubscriptionRead)
def expire_subscription(company_id: uuid.UUID, subscription_id: uuid.UUID, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> SubscriptionRead:
    return subscription_service.expire_subscription(db, company_id, subscription_id, actor_staff=admin)


@router.get("/companies/{company_id}/events", response_model=list[SubscriptionEventRead])
def company_subscription_events(company_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[SubscriptionEventRead]:
    return subscription_service.list_events(db, company_id)


# ---- PLAT-030: invoices and payment verification --------------------------------------------


@router.get("/companies/{company_id}/invoices", response_model=list[InvoiceRead])
def list_company_invoices(company_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[InvoiceRead]:
    return invoice_service.list_invoices(db, company_id)


@router.get("/payments/pending", response_model=list[PaymentSubmissionRead])
def list_pending_payments(db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[PaymentSubmissionRead]:
    return invoice_service.list_pending_payments(db)


@router.post("/payments/{submission_id}/verify", response_model=PaymentSubmissionRead)
def verify_payment(submission_id: uuid.UUID, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> PaymentSubmissionRead:
    return invoice_service.verify_payment(db, admin, submission_id)


@router.post("/payments/{submission_id}/reject", response_model=PaymentSubmissionRead)
def reject_payment(submission_id: uuid.UUID, payload: RejectPaymentRequest, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> PaymentSubmissionRead:
    return invoice_service.reject_payment(db, admin, submission_id, payload.reason)


# ---- Dashboards ---------------------------------------------------------------------------


@router.get("/overview")
def billing_overview(db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> dict:
    active_count = db.query(func.count(CompanySubscription.id)).filter(CompanySubscription.status.in_(["active", "trialing"])).scalar() or 0
    trialing_count = db.query(func.count(CompanySubscription.id)).filter(CompanySubscription.status == "trialing").scalar() or 0
    grace_count = db.query(func.count(CompanySubscription.id)).filter(CompanySubscription.status == "grace_period").scalar() or 0
    pending_payments_count = len(invoice_service.list_pending_payments(db))
    paid_total = db.query(func.coalesce(func.sum(SubscriptionInvoice.total_amount), 0)).filter(SubscriptionInvoice.status == InvoiceStatus.PAID).scalar() or 0
    return {
        "active_subscriptions": active_count,
        "trialing_subscriptions": trialing_count,
        "in_grace_period": grace_count,
        "pending_payments": pending_payments_count,
        "total_revenue_collected": str(paid_total),
    }


# ---- PLAT-032: legacy entitlement review ------------------------------------------------------


@router.get("/legacy-entitlements", response_model=list[LegacyEntitlementRead])
def list_legacy_entitlements(db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[LegacyEntitlementRead]:
    rows = (
        db.query(CompanyLegacyEntitlement, Company.name)
        .join(Company, Company.id == CompanyLegacyEntitlement.company_id)
        .order_by(CompanyLegacyEntitlement.created_at.asc())
        .all()
    )
    return [
        LegacyEntitlementRead(id=e.id, company_id=e.company_id, company_name=name, reason=e.reason, granted_by_staff_id=e.granted_by_staff_id, revoked_at=e.revoked_at, created_at=e.created_at)
        for e, name in rows
    ]


@router.post("/legacy-entitlements/{entitlement_id}/revoke", response_model=LegacyEntitlementRead)
def revoke_legacy_entitlement(entitlement_id: uuid.UUID, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> LegacyEntitlementRead:
    entitlement = db.query(CompanyLegacyEntitlement).filter(CompanyLegacyEntitlement.id == entitlement_id).first()
    if not entitlement:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Legacy entitlement not found")
    entitlement.revoked_at = datetime.now(timezone.utc)
    entitlement.revoked_by_staff_id = admin.id
    platform_audit_service.record(db, admin.id, "billing.legacy_entitlement_revoked", "company", entitlement.company_id, "Legacy (grandfathered) entitlement revoked")
    db.commit()
    db.refresh(entitlement)
    name = db.query(Company.name).filter(Company.id == entitlement.company_id).scalar()
    return LegacyEntitlementRead(id=entitlement.id, company_id=entitlement.company_id, company_name=name, reason=entitlement.reason, granted_by_staff_id=entitlement.granted_by_staff_id, revoked_at=entitlement.revoked_at, created_at=entitlement.created_at)
