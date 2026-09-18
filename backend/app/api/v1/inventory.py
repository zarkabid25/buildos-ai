import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.inventory import (
    InventoryDashboard,
    InventoryTransactionRead,
    MaterialStockLevel,
    StockInRequest,
    StockOutRequest,
    TransferRequest,
)
from app.services import inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.STOREKEEPER)


@router.get("/dashboard", response_model=InventoryDashboard)
def dashboard(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> InventoryDashboard:
    return inventory_service.get_dashboard(db, current_user.company_id)


@router.get("/stock", response_model=list[MaterialStockLevel])
def stock_levels(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialStockLevel]:
    return inventory_service.list_stock_levels(db, current_user.company_id)


@router.get("/transactions", response_model=list[InventoryTransactionRead])
def transactions(
    material_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InventoryTransactionRead]:
    return inventory_service.list_transactions(db, current_user.company_id, material_id)


@router.post("/stock-in", response_model=InventoryTransactionRead, status_code=201)
def stock_in(
    payload: StockInRequest,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> InventoryTransactionRead:
    return inventory_service.stock_in(db, current_user.company_id, current_user.id, payload)


@router.post("/stock-out", response_model=InventoryTransactionRead, status_code=201)
def stock_out(
    payload: StockOutRequest,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> InventoryTransactionRead:
    return inventory_service.stock_out(db, current_user.company_id, current_user.id, payload)


@router.post("/transfer", response_model=list[InventoryTransactionRead], status_code=201)
def transfer(
    payload: TransferRequest,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> list[InventoryTransactionRead]:
    out_tx, in_tx = inventory_service.transfer(db, current_user.company_id, current_user.id, payload)
    return [out_tx, in_tx]
