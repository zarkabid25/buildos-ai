import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.payment import (
    CashSummary,
    ClientReceiptCreate,
    ClientReceiptRead,
    SupplierPaymentCreate,
    SupplierPaymentRead,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

# Recording money movements is for finance roles only.
CAN_RECORD = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.ACCOUNTANT)


@router.get("/summary", response_model=CashSummary)
def summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CashSummary:
    return payment_service.cash_summary(db, current_user.company_id)


@router.get("/supplier", response_model=list[SupplierPaymentRead])
def list_supplier_payments(
    purchase_order_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SupplierPaymentRead]:
    return payment_service.list_supplier_payments(db, current_user.company_id, purchase_order_id)


@router.post("/supplier", response_model=SupplierPaymentRead, status_code=201)
def record_supplier_payment(
    payload: SupplierPaymentCreate,
    current_user: User = Depends(require_roles(*CAN_RECORD)),
    db: Session = Depends(get_db),
) -> SupplierPaymentRead:
    payment = payment_service.record_supplier_payment(db, current_user.company_id, current_user.id, payload)
    return next(
        p for p in payment_service.list_supplier_payments(db, current_user.company_id, payment.purchase_order_id)
        if p.id == payment.id
    )


@router.get("/client", response_model=list[ClientReceiptRead])
def list_client_receipts(
    project_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClientReceiptRead]:
    return payment_service.list_client_receipts(db, current_user.company_id, project_id)


@router.post("/client", response_model=ClientReceiptRead, status_code=201)
def record_client_receipt(
    payload: ClientReceiptCreate,
    current_user: User = Depends(require_roles(*CAN_RECORD)),
    db: Session = Depends(get_db),
) -> ClientReceiptRead:
    receipt = payment_service.record_client_receipt(db, current_user.company_id, current_user.id, payload)
    return next(r for r in payment_service.list_client_receipts(db, current_user.company_id, receipt.project_id) if r.id == receipt.id)
