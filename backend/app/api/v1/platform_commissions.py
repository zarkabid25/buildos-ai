import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_platform_admin, require_platform_roles
from app.db.session import get_db
from app.models.commission import CommissionDispute, CommissionLedgerEntry, MarketplacePoAttribution, SupplierCommissionAgreement
from app.models.enums import CommissionDisputeStatus, CommissionInvoiceStatus
from app.models.marketplace_supplier import MarketplaceSupplier
from app.models.platform_admin import PlatformAdmin
from app.schemas.commission import (
    CommissionAdjustmentRequest,
    CommissionAgreementCreate,
    CommissionAgreementRead,
    CommissionDisputeCreate,
    CommissionDisputeRead,
    CommissionDisputeReview,
    CommissionInvoiceRead,
    CommissionLedgerEntryRead,
    CommissionMonthlyTrendPoint,
    CommissionPaymentCreate,
    CommissionPaymentRead,
    CommissionRevenueDashboard,
    GenerateCommissionInvoiceRequest,
    SupplierRevenueContribution,
)
from app.models.enums import PlatformStaffRole
from app.services import commission_agreement_service, commission_dispute_service, commission_invoice_service, commission_service

router = APIRouter(prefix="/platform/commissions", tags=["platform-commissions"])

# Same tier as every other mutating financial action in this project
# (billing plan edits, payment verification): support can view, not mutate.
_can_edit = require_platform_roles(PlatformStaffRole.OWNER, PlatformStaffRole.ADMIN)


# ---- PLAT-033: supplier commission agreements -----------------------------------------------


@router.post("/suppliers/{marketplace_supplier_id}/agreements", response_model=CommissionAgreementRead, status_code=201)
def create_agreement(marketplace_supplier_id: uuid.UUID, payload: CommissionAgreementCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionAgreementRead:
    return commission_agreement_service.create_agreement(db, admin, marketplace_supplier_id, payload)


@router.get("/suppliers/{marketplace_supplier_id}/agreements", response_model=list[CommissionAgreementRead])
def list_agreements(marketplace_supplier_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[CommissionAgreementRead]:
    return commission_agreement_service.list_agreements(db, marketplace_supplier_id)


@router.post("/agreements/{agreement_id}/cancel", response_model=CommissionAgreementRead)
def cancel_agreement(agreement_id: uuid.UUID, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionAgreementRead:
    return commission_agreement_service.cancel_agreement(db, admin, agreement_id)


@router.get("/agreements", response_model=list[CommissionAgreementRead])
def list_all_active_agreements(db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> list[CommissionAgreementRead]:
    return commission_agreement_service.list_all_active_agreements(db)


# ---- PLAT-034: commission ledger -------------------------------------------------------------


@router.get("/ledger", response_model=list[CommissionLedgerEntryRead])
def list_ledger(
    marketplace_supplier_id: uuid.UUID | None = None,
    purchase_order_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[CommissionLedgerEntryRead]:
    return commission_service.list_ledger(db, marketplace_supplier_id, purchase_order_id)


@router.post("/ledger/adjustments", response_model=CommissionLedgerEntryRead, status_code=201)
def post_adjustment(payload: CommissionAdjustmentRequest, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionLedgerEntryRead:
    from app.models.procurement import PurchaseOrder

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == payload.purchase_order_id).first()
    company_id = po.company_id if po else None
    entry = commission_service.post_adjustment(db, company_id, payload.purchase_order_id, payload.marketplace_supplier_id, payload.amount, admin, payload.note)
    db.commit()
    return commission_service.to_read(entry)


# ---- PLAT-036: disputes -----------------------------------------------------------------------


@router.post("/disputes", response_model=CommissionDisputeRead, status_code=201)
def raise_dispute(payload: CommissionDisputeCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionDisputeRead:
    return commission_dispute_service.raise_dispute(db, admin, payload.ledger_entry_id, payload.reason)


@router.post("/disputes/{dispute_id}/review", response_model=CommissionDisputeRead)
def review_dispute(dispute_id: uuid.UUID, payload: CommissionDisputeReview, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionDisputeRead:
    return commission_dispute_service.review_dispute(db, admin, dispute_id, payload.approve, payload.resolution_notes)


@router.get("/disputes", response_model=list[CommissionDisputeRead])
def list_disputes(
    marketplace_supplier_id: uuid.UUID | None = None,
    status: CommissionDisputeStatus | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[CommissionDisputeRead]:
    return commission_dispute_service.list_disputes(db, marketplace_supplier_id, status)


# ---- PLAT-035: commission invoices and payments ------------------------------------------------


@router.post("/invoices", response_model=CommissionInvoiceRead, status_code=201)
def generate_invoice(payload: GenerateCommissionInvoiceRequest, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionInvoiceRead:
    return commission_invoice_service.generate_invoice(db, admin, payload.marketplace_supplier_id, payload.period_start, payload.period_end, payload.due_date)


@router.get("/invoices", response_model=list[CommissionInvoiceRead])
def list_invoices(
    marketplace_supplier_id: uuid.UUID | None = None,
    status: CommissionInvoiceStatus | None = None,
    db: Session = Depends(get_db),
    _admin: PlatformAdmin = Depends(get_current_platform_admin),
) -> list[CommissionInvoiceRead]:
    return commission_invoice_service.list_invoices(db, marketplace_supplier_id, status)


@router.get("/invoices/{invoice_id}", response_model=CommissionInvoiceRead)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> CommissionInvoiceRead:
    return commission_invoice_service.get_invoice(db, invoice_id)


@router.post("/invoices/{invoice_id}/payments", response_model=CommissionInvoiceRead, status_code=201)
def record_payment(invoice_id: uuid.UUID, payload: CommissionPaymentCreate, db: Session = Depends(get_db), admin: PlatformAdmin = Depends(_can_edit)) -> CommissionInvoiceRead:
    return commission_invoice_service.record_payment(db, admin, invoice_id, payload)


# ---- PLAT-037: revenue dashboard ----------------------------------------------------------------


@router.get("/revenue", response_model=CommissionRevenueDashboard)
def revenue_dashboard(db: Session = Depends(get_db), _admin: PlatformAdmin = Depends(get_current_platform_admin)) -> CommissionRevenueDashboard:
    entries = db.query(CommissionLedgerEntry).all()
    commission_earned = sum((e.commission_amount for e in entries), Decimal("0")).quantize(Decimal("0.01"))

    invoiced_total = db.query(func.coalesce(func.sum(CommissionLedgerEntry.commission_amount), 0)).filter(CommissionLedgerEntry.invoiced.is_(True)).scalar() or Decimal("0")

    from app.models.commission import CommissionInvoice, CommissionPayment

    collected_total = db.query(func.coalesce(func.sum(CommissionPayment.amount), 0)).scalar() or Decimal("0")
    outstanding = (Decimal(str(invoiced_total)) - Decimal(str(collected_total))).quantize(Decimal("0.01"))

    active_agreements = db.query(func.count(SupplierCommissionAgreement.id)).filter(SupplierCommissionAgreement.status == "active").scalar() or 0

    attributed = db.query(MarketplacePoAttribution).all()
    attributed_value = sum((a.attributed_amount for a in attributed), Decimal("0")).quantize(Decimal("0.01"))

    disputed_entry_ids = {d.ledger_entry_id for d in db.query(CommissionDispute).filter(CommissionDispute.status == CommissionDisputeStatus.OPEN).all()}
    disputed_amount = Decimal("0")
    if disputed_entry_ids:
        disputed_amount = sum(
            (e.commission_amount for e in db.query(CommissionLedgerEntry).filter(CommissionLedgerEntry.id.in_(disputed_entry_ids)).all()), Decimal("0")
        ).quantize(Decimal("0.01"))

    trend_map: dict[str, Decimal] = {}
    for e in entries:
        key = e.created_at.strftime("%Y-%m")
        trend_map[key] = trend_map.get(key, Decimal("0")) + e.commission_amount

    contribution_map: dict[uuid.UUID, Decimal] = {}
    for e in entries:
        contribution_map[e.marketplace_supplier_id] = contribution_map.get(e.marketplace_supplier_id, Decimal("0")) + e.commission_amount
    names = dict(db.query(MarketplaceSupplier.id, MarketplaceSupplier.name).filter(MarketplaceSupplier.id.in_(contribution_map)).all()) if contribution_map else {}

    return CommissionRevenueDashboard(
        commission_earned=commission_earned,
        commission_invoiced=Decimal(str(invoiced_total)).quantize(Decimal("0.01")),
        commission_collected=Decimal(str(collected_total)).quantize(Decimal("0.01")),
        outstanding_commission=outstanding,
        active_agreements=active_agreements,
        marketplace_attributed_order_count=len(attributed),
        marketplace_attributed_order_value=attributed_value,
        disputed_amount=disputed_amount,
        monthly_trend=[CommissionMonthlyTrendPoint(month=k, amount=v.quantize(Decimal("0.01"))) for k, v in sorted(trend_map.items())],
        supplier_contributions=sorted(
            [SupplierRevenueContribution(marketplace_supplier_id=sid, marketplace_supplier_name=names.get(sid, "Unknown"), commission_earned=amt.quantize(Decimal("0.01"))) for sid, amt in contribution_map.items()],
            key=lambda c: c.commission_earned, reverse=True,
        ),
    )
