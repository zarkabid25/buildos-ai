import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.procurement import (
    GoodsReceiptCreate,
    GoodsReceiptRead,
    MaterialRequestCreate,
    MaterialRequestRead,
    MaterialRequestStatusUpdate,
    PurchaseOrderCreate,
    PurchaseOrderRead,
)
from app.services import procurement_service

router = APIRouter(tags=["procurement"])

CAN_REQUEST = (
    UserRole.SUPER_ADMIN,
    UserRole.COMPANY_ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
    UserRole.STOREKEEPER,
)
CAN_APPROVE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER)
CAN_RECEIVE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.STOREKEEPER)

# ---- Material requests -----------------------------------------------------


@router.get("/material-requests", response_model=list[MaterialRequestRead])
def list_material_requests(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[MaterialRequestRead]:
    return procurement_service.list_material_requests(db, current_user.company_id)


@router.post("/material-requests", response_model=MaterialRequestRead, status_code=201)
def create_material_request(
    payload: MaterialRequestCreate,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> MaterialRequestRead:
    return procurement_service.create_material_request(db, current_user.company_id, current_user.id, payload)


@router.get("/material-requests/{request_id}", response_model=MaterialRequestRead)
def get_material_request(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaterialRequestRead:
    return procurement_service.get_material_request(db, current_user.company_id, request_id)


@router.patch("/material-requests/{request_id}/status", response_model=MaterialRequestRead)
def update_material_request_status(
    request_id: uuid.UUID,
    payload: MaterialRequestStatusUpdate,
    current_user: User = Depends(require_roles(*CAN_APPROVE)),
    db: Session = Depends(get_db),
) -> MaterialRequestRead:
    return procurement_service.update_material_request_status(
        db, current_user.company_id, request_id, payload.status
    )


# ---- Purchase orders --------------------------------------------------------


@router.get("/purchase-orders", response_model=list[PurchaseOrderRead])
def list_purchase_orders(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[PurchaseOrderRead]:
    return procurement_service.list_purchase_orders(db, current_user.company_id)


@router.post("/purchase-orders", response_model=PurchaseOrderRead, status_code=201)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    current_user: User = Depends(require_roles(*CAN_REQUEST)),
    db: Session = Depends(get_db),
) -> PurchaseOrderRead:
    return procurement_service.create_purchase_order(db, current_user.company_id, current_user.id, payload)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderRead)
def get_purchase_order(
    po_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PurchaseOrderRead:
    return procurement_service.get_purchase_order(db, current_user.company_id, po_id)


@router.post("/purchase-orders/{po_id}/approve", response_model=PurchaseOrderRead)
def approve_purchase_order(
    po_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_APPROVE)),
    db: Session = Depends(get_db),
) -> PurchaseOrderRead:
    return procurement_service.approve_purchase_order(db, current_user.company_id, current_user.id, po_id)


@router.post("/purchase-orders/{po_id}/goods-receipts", response_model=GoodsReceiptRead, status_code=201)
def create_goods_receipt(
    po_id: uuid.UUID,
    payload: GoodsReceiptCreate,
    current_user: User = Depends(require_roles(*CAN_RECEIVE)),
    db: Session = Depends(get_db),
) -> GoodsReceiptRead:
    return procurement_service.create_goods_receipt(
        db, current_user.company_id, current_user.id, po_id, payload
    )
