import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.storage import resolve_path
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.billing import (
    EntitlementRead,
    InvoiceRead,
    PaymentSubmissionRead,
    PlanChangeRequest,
    SubscriptionCreate,
    SubscriptionEventRead,
    SubscriptionPlanRead,
    SubscriptionRead,
)
from app.services import entitlement_service, invoice_service, subscription_plan_service, subscription_service

router = APIRouter(prefix="/billing", tags=["billing"])

# Only company admins/super admins manage billing -- the same two roles that
# can edit company settings today (see app/api/v1/companies.py).
CAN_MANAGE_BILLING = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)


@router.get("/plans", response_model=list[SubscriptionPlanRead])
def available_plans(db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[SubscriptionPlanRead]:
    return subscription_plan_service.list_plans(db, include_inactive=False)


@router.get("/subscription", response_model=SubscriptionRead | None)
def current_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> SubscriptionRead | None:
    return subscription_service.get_current_subscription_read(db, current_user.company_id)


@router.post("/subscriptions", response_model=SubscriptionRead, status_code=201)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(*CAN_MANAGE_BILLING))) -> SubscriptionRead:
    sub = subscription_service.create_subscription(db, current_user.company_id, current_user, payload)
    # Trialing subscriptions aren't billed yet; a real invoice is generated the
    # moment there's something to actually pay (PENDING_PAYMENT, or later at
    # renewal -- see activate_subscription's caller in invoice_service).
    if sub.status.value == "pending_payment":
        plan = subscription_plan_service.get_plan_model(db, sub.plan_id)
        price = subscription_plan_service.get_current_price(db, sub.plan_id, payload.currency, payload.billing_period)
        today = date.today()
        period_days = 365 if payload.billing_period.value == "annual" else 30
        invoice_service.generate_subscription_invoice(
            db, current_user.company_id, sub.id, plan.name, payload.currency, price.amount,
            today, today + timedelta(days=period_days), today + timedelta(days=7),
        )
        db.commit()
    return sub


@router.post("/subscriptions/{subscription_id}/change-plan", response_model=SubscriptionRead)
def change_plan(subscription_id: uuid.UUID, payload: PlanChangeRequest, db: Session = Depends(get_db), current_user: User = Depends(require_roles(*CAN_MANAGE_BILLING))) -> SubscriptionRead:
    return subscription_service.change_plan(db, current_user.company_id, current_user, subscription_id, payload)


@router.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionRead)
def cancel_subscription(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_roles(*CAN_MANAGE_BILLING))) -> SubscriptionRead:
    return subscription_service.cancel_subscription(db, current_user.company_id, current_user, subscription_id)


@router.get("/subscriptions/{subscription_id}/events", response_model=list[SubscriptionEventRead])
def subscription_events(subscription_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[SubscriptionEventRead]:
    return subscription_service.list_events(db, current_user.company_id, subscription_id)


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[InvoiceRead]:
    return invoice_service.list_invoices(db, current_user.company_id)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> InvoiceRead:
    return invoice_service.get_invoice(db, current_user.company_id, invoice_id)


@router.post("/invoices/{invoice_id}/payments", response_model=PaymentSubmissionRead, status_code=201)
async def submit_payment(
    invoice_id: uuid.UUID,
    file: UploadFile,
    amount: Decimal = Form(...),
    reference: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CAN_MANAGE_BILLING)),
) -> PaymentSubmissionRead:
    return await invoice_service.submit_payment(db, current_user.company_id, current_user, invoice_id, amount, reference, file)


@router.get("/payments/{submission_id}/proof")
def download_payment_proof(submission_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FileResponse:
    submission = invoice_service.get_payment_submission(db, current_user.company_id, submission_id)
    path = resolve_path(submission.proof_storage_key)
    return FileResponse(path, media_type=submission.proof_content_type, filename=submission.proof_filename)


@router.get("/entitlements", response_model=EntitlementRead)
def entitlements(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> EntitlementRead:
    return entitlement_service.get_effective_entitlements(db, current_user.company_id)
