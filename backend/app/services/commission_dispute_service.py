"""Commission disputes (PLAT-036). Approving a dispute never edits the
disputed ledger entry -- it calls commission_service.reverse_entry to post a
brand new REVERSAL entry and records that entry's id here, so both the
original charge and the fact it was reversed stay visible forever."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.commission import CommissionDispute
from app.models.enums import CommissionDisputeStatus, CommissionLedgerEntryKind
from app.models.platform_admin import PlatformAdmin
from app.schemas.commission import CommissionDisputeRead
from app.services import commission_service, platform_audit_service


def _read(d: CommissionDispute, raised_by: str | None = None, reviewed_by: str | None = None) -> CommissionDisputeRead:
    return CommissionDisputeRead(
        id=d.id, ledger_entry_id=d.ledger_entry_id, marketplace_supplier_id=d.marketplace_supplier_id, reason=d.reason,
        status=d.status, raised_by_staff_id=d.raised_by_staff_id, raised_by_staff_name=raised_by,
        reviewed_by_staff_id=d.reviewed_by_staff_id, reviewed_by_staff_name=reviewed_by,
        resolution_notes=d.resolution_notes, resulting_entry_id=d.resulting_entry_id, reviewed_at=d.reviewed_at, created_at=d.created_at,
    )


def raise_dispute(db: Session, actor: PlatformAdmin, ledger_entry_id: uuid.UUID, reason: str) -> CommissionDisputeRead:
    entry = commission_service.get_ledger_entry(db, ledger_entry_id)
    if entry.kind != CommissionLedgerEntryKind.ACCRUAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only an original accrual entry can be disputed, not a reversal or adjustment")
    existing_open = db.query(CommissionDispute).filter(CommissionDispute.ledger_entry_id == ledger_entry_id, CommissionDispute.status == CommissionDisputeStatus.OPEN).first()
    if existing_open:
        raise HTTPException(status.HTTP_409_CONFLICT, "This entry already has an open dispute")

    dispute = CommissionDispute(
        ledger_entry_id=ledger_entry_id,
        marketplace_supplier_id=entry.marketplace_supplier_id,
        reason=reason,
        raised_by_staff_id=actor.id,
    )
    db.add(dispute)
    db.flush()
    platform_audit_service.record(db, actor.id, "commission.dispute_raised", "commission_ledger_entry", ledger_entry_id, f"Dispute raised: {reason[:200]}")
    db.commit()
    db.refresh(dispute)
    return _read(dispute, actor.full_name)


def review_dispute(db: Session, actor: PlatformAdmin, dispute_id: uuid.UUID, approve: bool, resolution_notes: str) -> CommissionDisputeRead:
    dispute = db.query(CommissionDispute).filter(CommissionDispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dispute not found")
    if dispute.status != CommissionDisputeStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"This dispute was already {dispute.status.value}")

    if approve:
        reversal = commission_service.reverse_entry(db, dispute.ledger_entry_id, actor, f"Approved dispute: {resolution_notes[:200]}")
        dispute.resulting_entry_id = reversal.id
        dispute.status = CommissionDisputeStatus.APPROVED
    else:
        dispute.status = CommissionDisputeStatus.REJECTED

    dispute.reviewed_by_staff_id = actor.id
    dispute.resolution_notes = resolution_notes
    dispute.reviewed_at = datetime.now(timezone.utc)
    platform_audit_service.record(
        db, actor.id, "commission.dispute_reviewed", "commission_dispute", dispute.id,
        f"Dispute {'approved' if approve else 'rejected'}: {resolution_notes[:200]}",
    )
    db.commit()
    db.refresh(dispute)
    return _read(dispute, reviewed_by=actor.full_name)


def list_disputes(db: Session, marketplace_supplier_id: uuid.UUID | None = None, status_filter: CommissionDisputeStatus | None = None) -> list[CommissionDisputeRead]:
    from app.models.platform_admin import PlatformAdmin as PA

    raised = PA.__table__.alias("raised_staff")
    reviewed = PA.__table__.alias("reviewed_staff")
    query = (
        db.query(CommissionDispute, raised.c.full_name, reviewed.c.full_name)
        .outerjoin(raised, raised.c.id == CommissionDispute.raised_by_staff_id)
        .outerjoin(reviewed, reviewed.c.id == CommissionDispute.reviewed_by_staff_id)
    )
    if marketplace_supplier_id:
        query = query.filter(CommissionDispute.marketplace_supplier_id == marketplace_supplier_id)
    if status_filter:
        query = query.filter(CommissionDispute.status == status_filter)
    rows = query.order_by(CommissionDispute.created_at.desc()).all()
    return [_read(d, raised_name, reviewed_name) for d, raised_name, reviewed_name in rows]
