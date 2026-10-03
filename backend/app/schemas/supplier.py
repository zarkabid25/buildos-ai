import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import PurchaseOrderStatus


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SupplierContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class SupplierContactCreate(SupplierContactBase):
    pass


class SupplierContactRead(SupplierContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    created_at: datetime


class SupplierTransaction(BaseModel):
    """One purchase order placed with the supplier, with what has been received against it."""

    purchase_order_id: uuid.UUID
    po_number: str
    project_id: uuid.UUID | None
    project_name: str | None
    status: PurchaseOrderStatus
    created_at: datetime
    ordered_amount: Decimal
    received_amount: Decimal
    receipt_count: int
    last_received_at: datetime | None


class SupplierPerformance(BaseModel):
    po_count: int
    committed_po_count: int
    fully_received_count: int
    cancelled_count: int
    committed_amount: Decimal
    received_amount: Decimal
    # received / committed value over approved-or-later POs; None with nothing committed.
    fulfilment_percent: Decimal | None
    # Mean days from PO creation to its first goods receipt; None until something is received.
    average_lead_time_days: Decimal | None
    note: str = (
        "Purchase orders have no promised delivery date yet, so on-time delivery can't be "
        "measured; lead time is PO creation to first goods receipt."
    )
