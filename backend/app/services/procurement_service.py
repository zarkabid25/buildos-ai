import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.enums import InventoryTransactionType, MaterialRequestStatus, PurchaseOrderStatus
from app.models.inventory_transaction import InventoryTransaction
from app.models.procurement import (
    GoodsReceipt,
    GoodsReceiptItem,
    MaterialRequest,
    MaterialRequestItem,
    PurchaseOrder,
    PurchaseOrderItem,
)
from app.schemas.procurement import (
    GoodsReceiptCreate,
    MaterialRequestCreate,
    PurchaseOrderCreate,
)
from app.services.material_service import get_material
from app.services.project_service import get_project
from app.services.supplier_service import get_supplier
from app.services.warehouse_service import get_warehouse

# ---- Material requests ----------------------------------------------------


def list_material_requests(db: Session, company_id: uuid.UUID) -> list[MaterialRequest]:
    return (
        db.query(MaterialRequest)
        .options(joinedload(MaterialRequest.items))
        .filter(MaterialRequest.company_id == company_id)
        .order_by(MaterialRequest.created_at.desc())
        .all()
    )


def get_material_request(db: Session, company_id: uuid.UUID, request_id: uuid.UUID) -> MaterialRequest:
    req = (
        db.query(MaterialRequest)
        .options(joinedload(MaterialRequest.items))
        .filter(MaterialRequest.company_id == company_id, MaterialRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material request not found")
    return req


def create_material_request(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: MaterialRequestCreate
) -> MaterialRequest:
    get_project(db, company_id, payload.project_id)
    for item in payload.items:
        get_material(db, company_id, item.material_id)

    req = MaterialRequest(
        company_id=company_id,
        project_id=payload.project_id,
        requested_by_id=user_id,
        notes=payload.notes,
    )
    db.add(req)
    db.flush()

    for item in payload.items:
        db.add(
            MaterialRequestItem(
                company_id=company_id,
                material_request_id=req.id,
                material_id=item.material_id,
                quantity=item.quantity,
            )
        )
    db.commit()
    db.refresh(req)
    return req


def update_material_request_status(
    db: Session, company_id: uuid.UUID, request_id: uuid.UUID, new_status: MaterialRequestStatus
) -> MaterialRequest:
    req = get_material_request(db, company_id, request_id)
    if req.status != MaterialRequestStatus.PENDING:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a pending request can change status")
    req.status = new_status
    db.commit()
    db.refresh(req)
    return req


# ---- Purchase orders --------------------------------------------------------


def _next_po_number(db: Session, company_id: uuid.UUID) -> str:
    count = db.query(PurchaseOrder).filter(PurchaseOrder.company_id == company_id).count()
    return f"PO-{1000 + count + 1}"


def list_purchase_orders(db: Session, company_id: uuid.UUID) -> list[PurchaseOrder]:
    return (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.company_id == company_id)
        .order_by(PurchaseOrder.created_at.desc())
        .all()
    )


def get_purchase_order(db: Session, company_id: uuid.UUID, po_id: uuid.UUID) -> PurchaseOrder:
    po = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.items))
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.id == po_id)
        .first()
    )
    if not po:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po


def create_purchase_order(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: PurchaseOrderCreate
) -> PurchaseOrder:
    get_supplier(db, company_id, payload.supplier_id)
    if payload.project_id:
        get_project(db, company_id, payload.project_id)
    for item in payload.items:
        get_material(db, company_id, item.material_id)

    po = PurchaseOrder(
        company_id=company_id,
        supplier_id=payload.supplier_id,
        project_id=payload.project_id,
        material_request_id=payload.material_request_id,
        created_by_id=user_id,
        status=PurchaseOrderStatus.PENDING_APPROVAL,
        po_number=_next_po_number(db, company_id),
    )
    db.add(po)
    db.flush()

    for item in payload.items:
        db.add(
            PurchaseOrderItem(
                company_id=company_id,
                purchase_order_id=po.id,
                material_id=item.material_id,
                quantity=item.quantity,
                rate=item.rate,
            )
        )

    if payload.material_request_id:
        req = get_material_request(db, company_id, payload.material_request_id)
        if req.status == MaterialRequestStatus.PENDING:
            req.status = MaterialRequestStatus.CONVERTED

    db.commit()
    db.refresh(po)
    return po


def approve_purchase_order(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, po_id: uuid.UUID
) -> PurchaseOrder:
    po = get_purchase_order(db, company_id, po_id)
    if po.status != PurchaseOrderStatus.PENDING_APPROVAL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a pending-approval PO can be approved")
    po.status = PurchaseOrderStatus.APPROVED
    po.approved_by_id = user_id
    db.commit()
    db.refresh(po)
    return po


# ---- Goods receipt (this is what actually moves inventory) -----------------


def create_goods_receipt(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, po_id: uuid.UUID, payload: GoodsReceiptCreate
) -> GoodsReceipt:
    po = get_purchase_order(db, company_id, po_id)
    if po.status not in (PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.PARTIALLY_RECEIVED):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Purchase order must be approved before receiving goods"
        )
    get_warehouse(db, company_id, payload.warehouse_id)

    po_items_by_id = {item.id: item for item in po.items}

    for line in payload.items:
        po_item = po_items_by_id.get(line.purchase_order_item_id)
        if not po_item:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "PO item does not belong to this purchase order")
        remaining = po_item.quantity - po_item.quantity_received
        if line.quantity_received > remaining:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot receive {line.quantity_received}: only {remaining} remaining on this PO item",
            )

    receipt = GoodsReceipt(
        company_id=company_id,
        purchase_order_id=po.id,
        warehouse_id=payload.warehouse_id,
        received_by_id=user_id,
    )
    db.add(receipt)
    db.flush()

    for line in payload.items:
        po_item = po_items_by_id[line.purchase_order_item_id]

        db.add(
            GoodsReceiptItem(
                company_id=company_id,
                goods_receipt_id=receipt.id,
                purchase_order_item_id=po_item.id,
                material_id=po_item.material_id,
                quantity_received=line.quantity_received,
            )
        )

        # This is BUILD-047: receiving goods automatically posts a STOCK_IN
        # transaction against the append-only inventory ledger (Day 6), so
        # stock levels reflect reality the moment goods are actually received,
        # with no separate manual "stock in" step for procurement-sourced stock.
        db.add(
            InventoryTransaction(
                company_id=company_id,
                material_id=po_item.material_id,
                warehouse_id=payload.warehouse_id,
                transaction_type=InventoryTransactionType.STOCK_IN,
                quantity=line.quantity_received,
                reference=po.po_number,
                notes=f"Goods receipt for {po.po_number}",
                created_by_id=user_id,
            )
        )

        po_item.quantity_received += line.quantity_received

    if all(item.quantity_received >= item.quantity for item in po.items):
        po.status = PurchaseOrderStatus.RECEIVED
    else:
        po.status = PurchaseOrderStatus.PARTIALLY_RECEIVED

    db.commit()
    db.refresh(receipt)
    return receipt
