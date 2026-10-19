"""Supplier commission agreements (PLAT-033). Versioned like billing's
PlanPrice: a "change" never edits a row, it supersedes it -- superseding
flips the old row to SUPERSEDED (with effective_to set to now) and inserts a
new ACTIVE one with version+1. The partial unique index on
(marketplace_supplier_id) WHERE status='active' is what actually prevents
two overlapping active agreements for the same supplier; this module's own
checks are a friendlier error message in front of that same guarantee, not
a substitute for it."""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.commission import SupplierCommissionAgreement
from app.models.enums import CommissionAgreementStatus
from app.models.platform_admin import PlatformAdmin
from app.schemas.commission import CommissionAgreementCreate, CommissionAgreementRead
from app.services import platform_audit_service


def _read(a: SupplierCommissionAgreement) -> CommissionAgreementRead:
    return CommissionAgreementRead.model_validate(a)


def get_active_agreement_for_date(db: Session, marketplace_supplier_id: uuid.UUID, as_of: date | datetime) -> SupplierCommissionAgreement | None:
    """An agreement applies only while effective_from <= as_of and
    (effective_to is null or effective_to > as_of) -- status alone isn't
    enough, since an ACTIVE row can still have a past effective_to if staff
    deliberately ended it without replacing it."""
    if isinstance(as_of, date) and not isinstance(as_of, datetime):
        # A plain date (e.g. a SupplierPayment.paid_on) has no time component
        # -- compare against the END of that calendar day, so an agreement
        # created earlier the same day (effective_from = an exact timestamp)
        # still correctly applies to a payment dated that same day.
        as_of = datetime(as_of.year, as_of.month, as_of.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
    elif as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    return (
        db.query(SupplierCommissionAgreement)
        .filter(
            SupplierCommissionAgreement.marketplace_supplier_id == marketplace_supplier_id,
            SupplierCommissionAgreement.status == CommissionAgreementStatus.ACTIVE,
            SupplierCommissionAgreement.effective_from <= as_of,
            (SupplierCommissionAgreement.effective_to.is_(None)) | (SupplierCommissionAgreement.effective_to > as_of),
        )
        .first()
    )


def create_agreement(db: Session, actor: PlatformAdmin, marketplace_supplier_id: uuid.UUID, payload: CommissionAgreementCreate) -> CommissionAgreementRead:
    now = datetime.now(timezone.utc)
    previous = (
        db.query(SupplierCommissionAgreement)
        .filter(SupplierCommissionAgreement.marketplace_supplier_id == marketplace_supplier_id, SupplierCommissionAgreement.status == CommissionAgreementStatus.ACTIVE)
        .first()
    )
    next_version = (previous.version + 1) if previous else 1
    if previous:
        previous.status = CommissionAgreementStatus.SUPERSEDED
        previous.effective_to = now

    agreement = SupplierCommissionAgreement(
        marketplace_supplier_id=marketplace_supplier_id,
        version=next_version,
        basis=payload.basis,
        rate=payload.rate,
        fixed_fee_amount=payload.fixed_fee_amount,
        earning_trigger=payload.earning_trigger,
        status=CommissionAgreementStatus.ACTIVE,
        effective_from=payload.effective_from or now,
        created_by_staff_id=actor.id,
        notes=payload.notes,
    )
    db.add(agreement)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This supplier already has an active commission agreement")

    platform_audit_service.record(
        db, actor.id, "commission.agreement_created", "marketplace_supplier", marketplace_supplier_id,
        f"Commission agreement v{next_version}: {payload.basis.value} "
        + (f"{payload.rate}" if payload.basis.value == "percentage" else f"{payload.fixed_fee_amount}"),
    )
    db.commit()
    db.refresh(agreement)
    return _read(agreement)


def cancel_agreement(db: Session, actor: PlatformAdmin, agreement_id: uuid.UUID) -> CommissionAgreementRead:
    agreement = db.query(SupplierCommissionAgreement).filter(SupplierCommissionAgreement.id == agreement_id).first()
    if not agreement:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agreement not found")
    if agreement.status != CommissionAgreementStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"This agreement is already {agreement.status.value}")
    agreement.status = CommissionAgreementStatus.CANCELLED
    agreement.effective_to = datetime.now(timezone.utc)
    platform_audit_service.record(db, actor.id, "commission.agreement_cancelled", "marketplace_supplier", agreement.marketplace_supplier_id, "Commission agreement cancelled")
    db.commit()
    db.refresh(agreement)
    return _read(agreement)


def list_agreements(db: Session, marketplace_supplier_id: uuid.UUID) -> list[CommissionAgreementRead]:
    rows = (
        db.query(SupplierCommissionAgreement)
        .filter(SupplierCommissionAgreement.marketplace_supplier_id == marketplace_supplier_id)
        .order_by(SupplierCommissionAgreement.version.desc())
        .all()
    )
    return [_read(a) for a in rows]


def list_all_active_agreements(db: Session) -> list[CommissionAgreementRead]:
    rows = db.query(SupplierCommissionAgreement).filter(SupplierCommissionAgreement.status == CommissionAgreementStatus.ACTIVE).order_by(SupplierCommissionAgreement.created_at.desc()).all()
    return [_read(a) for a in rows]
