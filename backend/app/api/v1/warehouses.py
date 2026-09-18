import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.warehouse import WarehouseCreate, WarehouseRead, WarehouseUpdate
from app.services import warehouse_service

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.STOREKEEPER)


@router.get("", response_model=list[WarehouseRead])
def list_warehouses(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[WarehouseRead]:
    return warehouse_service.list_warehouses(db, current_user.company_id)


@router.post("", response_model=WarehouseRead, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> WarehouseRead:
    return warehouse_service.create_warehouse(db, current_user.company_id, payload)


@router.patch("/{warehouse_id}", response_model=WarehouseRead)
def update_warehouse(
    warehouse_id: uuid.UUID,
    payload: WarehouseUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> WarehouseRead:
    return warehouse_service.update_warehouse(db, current_user.company_id, warehouse_id, payload)
