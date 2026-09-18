import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.warehouse import Warehouse
from app.schemas.warehouse import WarehouseCreate, WarehouseUpdate


def list_warehouses(db: Session, company_id: uuid.UUID) -> list[Warehouse]:
    return (
        db.query(Warehouse)
        .filter(Warehouse.company_id == company_id)
        .order_by(Warehouse.name.asc())
        .all()
    )


def get_warehouse(db: Session, company_id: uuid.UUID, warehouse_id: uuid.UUID) -> Warehouse:
    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.company_id == company_id, Warehouse.id == warehouse_id)
        .first()
    )
    if not warehouse:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Warehouse not found")
    return warehouse


def create_warehouse(db: Session, company_id: uuid.UUID, payload: WarehouseCreate) -> Warehouse:
    warehouse = Warehouse(company_id=company_id, **payload.model_dump())
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


def update_warehouse(
    db: Session, company_id: uuid.UUID, warehouse_id: uuid.UUID, payload: WarehouseUpdate
) -> Warehouse:
    warehouse = get_warehouse(db, company_id, warehouse_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(warehouse, field, value)
    db.commit()
    db.refresh(warehouse)
    return warehouse
