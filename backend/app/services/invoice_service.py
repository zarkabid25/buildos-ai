"""Invoices and manual (bank-transfer) payments (PLAT-030). Money is always
Decimal/Numeric, never float. Payment proof files reuse the same private-
storage backend and validation as every other upload in this app
(app/core/storage.py) -- never a public URL, always resolved through an
authorized download endpoint. Verifying is restricted to platform owner/admin
staff and can only ever happen once per submission (PENDING -> VERIFIED or
REJECTED is terminal), which is what prevents duplicate verification and a
second, accidental activation of the same subscription."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.storage import DOCUMENT_TYPES, save_upload
from app.models.billing import InvoiceLineItem, PaymentSubmission, SubscriptionInvoice
from app.models.company import Company
from app.models.enums import InvoiceStatus, PaymentSubmissionStatus
from app.models.platform_admin import PlatformAdmin
from app.models.user import User
from app.schemas.billing import AdminInvoiceRead, InvoiceLineItemRead, InvoiceRead, PaymentSubmissionRead
from app.services import audit_service, platform_audit_service, subscription_service


def _next_invoice_number(db: Session) -> str:
    count = db.query(SubscriptionInvoice).count()
    return f"INV-{10000 + count + 1}"


def _read(invoice: SubscriptionInvoice, staff_names: dict[uuid.UUID, str] | None = None) -> InvoiceRead:
    staff_names = staff_names or {}
    return InvoiceRead(
        id=invoice.id,
        company_id=invoice.company_id,
        subscription_id=invoice.subscription_id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        due_date=invoice.due_date,
        paid_at=invoice.paid_at,
        items=[InvoiceLineItemRead.model_validate(i) for i in invoice.items],
        payments=[
            PaymentSubmissionRead(
                id=p.id, invoice_id=p.invoice_id, company_id=p.company_id, submitted_by_user_id=p.submitted_by_user_id,
                amount=p.amount, method=p.method, reference=p.reference, proof_filename=p.proof_filename, status=p.status,
                verified_by_staff_id=p.verified_by_staff_id, verified_by_staff_name=staff_names.get(p.verified_by_staff_id) if p.verified_by_staff_id else None,
                verified_at=p.verified_at, rejection_reason=p.rejection_reason, created_at=p.created_at,
            )
            for p in invoice.payments
        ],
        created_at=invoice.created_at,
    )


def generate_subscription_invoice(
    db: Session,
    company_id: uuid.UUID,
    subscription_id: uuid.UUID,
    plan_name: str,
    currency: str,
    amount: Decimal,
    period_start: date,
    period_end: date,
    due_date: date,
    discount_amount: Decimal = Decimal("0"),
    tax_amount: Decimal = Decimal("0"),
) -> SubscriptionInvoice:
    """Called by subscription_service on creation/renewal -- never directly
    by a route, so an invoice is always tied to a real subscription event."""
    subtotal = amount
    total = (subtotal - discount_amount + tax_amount).quantize(Decimal("0.01"))
    invoice = SubscriptionInvoice(
        company_id=company_id,
        subscription_id=subscription_id,
        invoice_number=_next_invoice_number(db),
        status=InvoiceStatus.PENDING,
        currency=currency,
        subtotal=subtotal,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        total_amount=total,
        billing_period_start=period_start,
        billing_period_end=period_end,
        due_date=due_date,
    )
    db.add(invoice)
    db.flush()
    db.add(InvoiceLineItem(invoice_id=invoice.id, description=f"{plan_name} subscription", quantity=1, unit_price=amount, amount=amount))
    return invoice


def _get(db: Session, company_id: uuid.UUID, invoice_id: uuid.UUID) -> SubscriptionInvoice:
    invoice = (
        db.query(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.items), selectinload(SubscriptionInvoice.payments))
        .filter(SubscriptionInvoice.company_id == company_id, SubscriptionInvoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return invoice


def _get_staff_names(db: Session, invoice: SubscriptionInvoice) -> dict[uuid.UUID, str]:
    ids = [p.verified_by_staff_id for p in invoice.payments if p.verified_by_staff_id]
    if not ids:
        return {}
    return dict(db.query(PlatformAdmin.id, PlatformAdmin.full_name).filter(PlatformAdmin.id.in_(ids)).all())


def list_invoices(db: Session, company_id: uuid.UUID) -> list[InvoiceRead]:
    invoices = (
        db.query(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.items), selectinload(SubscriptionInvoice.payments))
        .filter(SubscriptionInvoice.company_id == company_id)
        .order_by(SubscriptionInvoice.created_at.desc())
        .all()
    )
    return [_read(inv, _get_staff_names(db, inv)) for inv in invoices]


def get_invoice(db: Session, company_id: uuid.UUID, invoice_id: uuid.UUID) -> InvoiceRead:
    invoice = _get(db, company_id, invoice_id)
    return _read(invoice, _get_staff_names(db, invoice))


def to_read(db: Session, invoice: SubscriptionInvoice) -> InvoiceRead:
    """Public wrapper around the private `_read` builder, for callers outside
    this module that already hold a real invoice row (e.g. the company-facing
    renewal endpoint in app/api/v1/billing.py)."""
    return _read(invoice, _get_staff_names(db, invoice))


def get_pending_invoice_for_subscription(db: Session, subscription_id: uuid.UUID) -> SubscriptionInvoice | None:
    """Used by the renewal endpoint to stay idempotent: if a subscription
    already has an unpaid invoice outstanding, a repeated renewal request
    must return that same invoice rather than generating a duplicate."""
    return (
        db.query(SubscriptionInvoice)
        .options(selectinload(SubscriptionInvoice.items), selectinload(SubscriptionInvoice.payments))
        .filter(SubscriptionInvoice.subscription_id == subscription_id, SubscriptionInvoice.status == InvoiceStatus.PENDING)
        .order_by(SubscriptionInvoice.created_at.desc())
        .first()
    )


def list_all_invoices(
    db: Session,
    company_id: uuid.UUID | None = None,
    status_filter: InvoiceStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[AdminInvoiceRead]:
    """Platform-wide invoice list for the admin billing screens (Task 2) --
    same rows list_invoices reads, just not scoped to one company, with real
    server-side filters instead of a frontend doing it with everything."""
    query = (
        db.query(SubscriptionInvoice, Company.name)
        .join(Company, Company.id == SubscriptionInvoice.company_id)
        .options(selectinload(SubscriptionInvoice.items), selectinload(SubscriptionInvoice.payments))
    )
    if company_id:
        query = query.filter(SubscriptionInvoice.company_id == company_id)
    if status_filter:
        query = query.filter(SubscriptionInvoice.status == status_filter)
    if date_from:
        query = query.filter(SubscriptionInvoice.created_at >= date_from)
    if date_to:
        query = query.filter(SubscriptionInvoice.created_at < date_to + timedelta(days=1))
    rows = query.order_by(SubscriptionInvoice.created_at.desc()).all()
    return [AdminInvoiceRead(**_read(invoice, _get_staff_names(db, invoice)).model_dump(), company_name=company_name) for invoice, company_name in rows]


async def submit_payment(
    db: Session, company_id: uuid.UUID, actor_user: User, invoice_id: uuid.UUID, amount: Decimal, reference: str | None, file: UploadFile
) -> PaymentSubmissionRead:
    invoice = _get(db, company_id, invoice_id)
    if invoice.status not in (InvoiceStatus.PENDING,):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This invoice is {invoice.status.value}, not awaiting payment")

    key, _size = await save_upload(file, company_id, "payment-proofs", DOCUMENT_TYPES)
    submission = PaymentSubmission(
        company_id=company_id,
        invoice_id=invoice_id,
        submitted_by_user_id=actor_user.id,
        amount=amount,
        reference=reference,
        proof_storage_key=key,
        proof_content_type=file.content_type or "application/octet-stream",
        proof_filename=(file.filename or "proof")[:255],
    )
    db.add(submission)
    audit_service.record(db, company_id, actor_user.id, "billing.payment_submitted", "subscription_invoice", invoice.id, f"Payment of {amount} {invoice.currency} submitted for {invoice.invoice_number}")
    db.commit()
    db.refresh(submission)
    return PaymentSubmissionRead(
        id=submission.id, invoice_id=submission.invoice_id, company_id=submission.company_id, submitted_by_user_id=submission.submitted_by_user_id,
        amount=submission.amount, method=submission.method, reference=submission.reference, proof_filename=submission.proof_filename, status=submission.status,
        verified_by_staff_id=None, verified_by_staff_name=None, verified_at=None, rejection_reason=None, created_at=submission.created_at,
    )


def get_payment_submission(db: Session, company_id: uuid.UUID, submission_id: uuid.UUID) -> PaymentSubmission:
    submission = db.query(PaymentSubmission).filter(PaymentSubmission.id == submission_id).first()
    if not submission or (company_id and submission.company_id != company_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment submission not found")
    return submission


def list_pending_payments(db: Session) -> list[PaymentSubmissionRead]:
    submissions = db.query(PaymentSubmission).filter(PaymentSubmission.status == PaymentSubmissionStatus.PENDING).order_by(PaymentSubmission.created_at.asc()).all()
    return [
        PaymentSubmissionRead(
            id=p.id, invoice_id=p.invoice_id, company_id=p.company_id, submitted_by_user_id=p.submitted_by_user_id,
            amount=p.amount, method=p.method, reference=p.reference, proof_filename=p.proof_filename, status=p.status,
            verified_by_staff_id=None, verified_by_staff_name=None, verified_at=None, rejection_reason=None, created_at=p.created_at,
        )
        for p in submissions
    ]


def verify_payment(db: Session, actor_staff: PlatformAdmin, submission_id: uuid.UUID, period_days: int = 30) -> PaymentSubmissionRead:
    submission = db.query(PaymentSubmission).filter(PaymentSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment submission not found")
    if submission.status != PaymentSubmissionStatus.PENDING:
        # Already verified or rejected -- refuses a second verification outright,
        # which is what stops a duplicate subscription activation.
        raise HTTPException(status.HTTP_409_CONFLICT, f"This payment was already {submission.status.value}")

    invoice = db.query(SubscriptionInvoice).filter(SubscriptionInvoice.id == submission.invoice_id).first()

    submission.status = PaymentSubmissionStatus.VERIFIED
    submission.verified_by_staff_id = actor_staff.id
    submission.verified_at = datetime.now(timezone.utc)
    invoice.status = InvoiceStatus.PAID
    invoice.paid_at = submission.verified_at

    platform_audit_service.record(db, actor_staff.id, "billing.payment_verified", "subscription_invoice", invoice.id, f"Payment of {submission.amount} {invoice.currency} verified for {invoice.invoice_number}")
    db.commit()

    subscription_service.activate_subscription(db, invoice.company_id, invoice.subscription_id, actor_staff, period_days=period_days)
    db.refresh(submission)
    return PaymentSubmissionRead(
        id=submission.id, invoice_id=submission.invoice_id, company_id=submission.company_id, submitted_by_user_id=submission.submitted_by_user_id,
        amount=submission.amount, method=submission.method, reference=submission.reference, proof_filename=submission.proof_filename, status=submission.status,
        verified_by_staff_id=submission.verified_by_staff_id, verified_by_staff_name=actor_staff.full_name, verified_at=submission.verified_at,
        rejection_reason=None, created_at=submission.created_at,
    )


def reject_payment(db: Session, actor_staff: PlatformAdmin, submission_id: uuid.UUID, reason: str) -> PaymentSubmissionRead:
    submission = db.query(PaymentSubmission).filter(PaymentSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payment submission not found")
    if submission.status != PaymentSubmissionStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This payment was already {submission.status.value}")

    submission.status = PaymentSubmissionStatus.REJECTED
    submission.verified_by_staff_id = actor_staff.id
    submission.verified_at = datetime.now(timezone.utc)
    submission.rejection_reason = reason

    invoice = db.query(SubscriptionInvoice).filter(SubscriptionInvoice.id == submission.invoice_id).first()
    platform_audit_service.record(db, actor_staff.id, "billing.payment_rejected", "subscription_invoice", invoice.id, f"Payment rejected for {invoice.invoice_number}: {reason}")
    db.commit()
    db.refresh(submission)
    return PaymentSubmissionRead(
        id=submission.id, invoice_id=submission.invoice_id, company_id=submission.company_id, submitted_by_user_id=submission.submitted_by_user_id,
        amount=submission.amount, method=submission.method, reference=submission.reference, proof_filename=submission.proof_filename, status=submission.status,
        verified_by_staff_id=submission.verified_by_staff_id, verified_by_staff_name=actor_staff.full_name, verified_at=submission.verified_at,
        rejection_reason=submission.rejection_reason, created_at=submission.created_at,
    )
