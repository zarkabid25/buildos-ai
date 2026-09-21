import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import InventoryTransactionType
from app.models.inventory_transaction import InventoryTransaction
from app.models.material import Material
from app.models.warehouse import Warehouse
from app.schemas.inventory import (
    InventoryDashboard,
    MaterialStockLevel,
    StockInRequest,
    StockOutRequest,
    TransferRequest,
)
from app.services.material_service import get_material
from app.services.warehouse_service import get_warehouse

_IN_TYPES = (InventoryTransactionType.STOCK_IN, InventoryTransactionType.TRANSFER_IN)
_OUT_TYPES = (
    InventoryTransactionType.STOCK_OUT,
    InventoryTransactionType.TRANSFER_OUT,
    InventoryTransactionType.ALLOCATION,
)


def get_stock_on_hand(
    db: Session, company_id: uuid.UUID, material_id: uuid.UUID, warehouse_id: uuid.UUID
) -> Decimal:
    rows = (
        db.query(InventoryTransaction.transaction_type, func.sum(InventoryTransaction.quantity))
        .filter(
            InventoryTransaction.company_id == company_id,
            InventoryTransaction.material_id == material_id,
            InventoryTransaction.warehouse_id == warehouse_id,
        )
        .group_by(InventoryTransaction.transaction_type)
        .all()
    )
    total = Decimal("0")
    for tx_type, qty in rows:
        if tx_type in _IN_TYPES:
            total += qty
        elif tx_type in _OUT_TYPES:
            total -= qty
    return total


def get_total_stock_on_hand(db: Session, company_id: uuid.UUID, material_id: uuid.UUID) -> Decimal:
    """Stock on hand for a material summed across every warehouse."""
    rows = (
        db.query(InventoryTransaction.transaction_type, func.sum(InventoryTransaction.quantity))
        .filter(InventoryTransaction.company_id == company_id, InventoryTransaction.material_id == material_id)
        .group_by(InventoryTransaction.transaction_type)
        .all()
    )
    total = Decimal("0")
    for tx_type, qty in rows:
        if tx_type in _IN_TYPES:
            total += qty
        elif tx_type in _OUT_TYPES:
            total -= qty
    return total


def stock_in(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: StockInRequest
) -> InventoryTransaction:
    get_material(db, company_id, payload.material_id)
    get_warehouse(db, company_id, payload.warehouse_id)

    tx = InventoryTransaction(
        company_id=company_id,
        material_id=payload.material_id,
        warehouse_id=payload.warehouse_id,
        transaction_type=InventoryTransactionType.STOCK_IN,
        quantity=payload.quantity,
        reference=payload.reference,
        notes=payload.notes,
        created_by_id=user_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def stock_out(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: StockOutRequest
) -> InventoryTransaction:
    get_material(db, company_id, payload.material_id)
    get_warehouse(db, company_id, payload.warehouse_id)

    on_hand = get_stock_on_hand(db, company_id, payload.material_id, payload.warehouse_id)
    if payload.quantity > on_hand:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Insufficient stock: {on_hand} available, {payload.quantity} requested",
        )

    tx_type = (
        InventoryTransactionType.ALLOCATION
        if payload.project_id
        else InventoryTransactionType.STOCK_OUT
    )
    tx = InventoryTransaction(
        company_id=company_id,
        material_id=payload.material_id,
        warehouse_id=payload.warehouse_id,
        project_id=payload.project_id,
        transaction_type=tx_type,
        quantity=payload.quantity,
        reference=payload.reference,
        notes=payload.notes,
        created_by_id=user_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def transfer(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: TransferRequest
) -> tuple[InventoryTransaction, InventoryTransaction]:
    if payload.from_warehouse_id == payload.to_warehouse_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source and destination warehouse must differ")

    get_material(db, company_id, payload.material_id)
    get_warehouse(db, company_id, payload.from_warehouse_id)
    get_warehouse(db, company_id, payload.to_warehouse_id)

    on_hand = get_stock_on_hand(db, company_id, payload.material_id, payload.from_warehouse_id)
    if payload.quantity > on_hand:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Insufficient stock at source warehouse: {on_hand} available, {payload.quantity} requested",
        )

    group_id = uuid.uuid4()
    out_tx = InventoryTransaction(
        company_id=company_id,
        material_id=payload.material_id,
        warehouse_id=payload.from_warehouse_id,
        transaction_type=InventoryTransactionType.TRANSFER_OUT,
        quantity=payload.quantity,
        notes=payload.notes,
        created_by_id=user_id,
        transfer_group_id=group_id,
    )
    in_tx = InventoryTransaction(
        company_id=company_id,
        material_id=payload.material_id,
        warehouse_id=payload.to_warehouse_id,
        transaction_type=InventoryTransactionType.TRANSFER_IN,
        quantity=payload.quantity,
        notes=payload.notes,
        created_by_id=user_id,
        transfer_group_id=group_id,
    )
    db.add_all([out_tx, in_tx])
    db.commit()
    db.refresh(out_tx)
    db.refresh(in_tx)
    return out_tx, in_tx


def list_stock_levels(db: Session, company_id: uuid.UUID) -> list[MaterialStockLevel]:
    materials = db.query(Material).filter(Material.company_id == company_id).all()
    warehouses = db.query(Warehouse).filter(Warehouse.company_id == company_id).all()

    levels: list[MaterialStockLevel] = []
    for material in materials:
        for warehouse in warehouses:
            qty = get_stock_on_hand(db, company_id, material.id, warehouse.id)
            if qty == 0:
                continue
            levels.append(
                MaterialStockLevel(
                    material_id=material.id,
                    material_name=material.name,
                    unit=material.unit,
                    warehouse_id=warehouse.id,
                    warehouse_name=warehouse.name,
                    quantity_on_hand=qty,
                )
            )
    return levels


def list_transactions(
    db: Session, company_id: uuid.UUID, material_id: uuid.UUID | None = None
) -> list[InventoryTransaction]:
    query = db.query(InventoryTransaction).filter(InventoryTransaction.company_id == company_id)
    if material_id:
        query = query.filter(InventoryTransaction.material_id == material_id)
    return query.order_by(InventoryTransaction.created_at.desc()).all()


def get_dashboard(db: Session, company_id: uuid.UUID) -> InventoryDashboard:
    materials = db.query(Material).filter(Material.company_id == company_id).all()
    warehouse_count = db.query(Warehouse).filter(Warehouse.company_id == company_id).count()

    low_stock = 0
    out_of_stock = 0
    for material in materials:
        total = get_total_stock_on_hand(db, company_id, material.id)
        if total <= 0:
            out_of_stock += 1
        elif total <= material.reorder_point:
            low_stock += 1

    return InventoryDashboard(
        total_materials=len(materials),
        low_stock_count=low_stock,
        out_of_stock_count=out_of_stock,
        warehouse_count=warehouse_count,
    )
