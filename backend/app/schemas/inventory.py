import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InventoryTransactionType


class StockInRequest(BaseModel):
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    reference: str | None = None
    notes: str | None = None


class StockOutRequest(BaseModel):
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    project_id: uuid.UUID | None = None
    reference: str | None = None
    notes: str | None = None


class TransferRequest(BaseModel):
    material_id: uuid.UUID
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    notes: str | None = None


class InventoryTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    warehouse_id: uuid.UUID
    project_id: uuid.UUID | None
    transaction_type: InventoryTransactionType
    quantity: Decimal
    reference: str | None
    notes: str | None
    created_by_id: uuid.UUID
    created_at: datetime


class MaterialStockLevel(BaseModel):
    material_id: uuid.UUID
    material_name: str
    unit: str
    warehouse_id: uuid.UUID
    warehouse_name: str
    quantity_on_hand: Decimal


class InventoryDashboard(BaseModel):
    total_materials: int
    low_stock_count: int
    out_of_stock_count: int
    warehouse_count: int
