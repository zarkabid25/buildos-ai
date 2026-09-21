import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MaterialRequestStatus, PurchaseOrderStatus


class MaterialRequestItemInput(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class MaterialRequestItemRead(MaterialRequestItemInput):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class MaterialRequestCreate(BaseModel):
    project_id: uuid.UUID
    notes: str | None = None
    items: list[MaterialRequestItemInput] = Field(min_length=1)


class MaterialRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    requested_by_id: uuid.UUID
    status: MaterialRequestStatus
    notes: str | None
    created_at: datetime
    items: list[MaterialRequestItemRead]


class MaterialRequestStatusUpdate(BaseModel):
    status: MaterialRequestStatus


class PurchaseOrderItemInput(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(gt=0)
    rate: Decimal = Field(ge=0)


class PurchaseOrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    material_id: uuid.UUID
    quantity: Decimal
    rate: Decimal
    quantity_received: Decimal
    amount: Decimal


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None = None
    material_request_id: uuid.UUID | None = None
    items: list[PurchaseOrderItemInput] = Field(min_length=1)


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    project_id: uuid.UUID | None
    material_request_id: uuid.UUID | None
    created_by_id: uuid.UUID
    approved_by_id: uuid.UUID | None
    status: PurchaseOrderStatus
    po_number: str
    created_at: datetime
    items: list[PurchaseOrderItemRead]
    total_amount: Decimal


class GoodsReceiptItemInput(BaseModel):
    purchase_order_item_id: uuid.UUID
    quantity_received: Decimal = Field(gt=0)


class GoodsReceiptCreate(BaseModel):
    warehouse_id: uuid.UUID
    items: list[GoodsReceiptItemInput] = Field(min_length=1)


class GoodsReceiptItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_item_id: uuid.UUID
    material_id: uuid.UUID
    quantity_received: Decimal


class GoodsReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    warehouse_id: uuid.UUID
    received_by_id: uuid.UUID
    created_at: datetime
    items: list[GoodsReceiptItemRead]
