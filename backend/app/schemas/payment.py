import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentMethod


class SupplierPaymentCreate(BaseModel):
    purchase_order_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    paid_on: date
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class ClientReceiptCreate(BaseModel):
    project_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    received_on: date
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class SupplierPaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purchase_order_id: uuid.UUID
    po_number: str | None = None
    supplier_name: str | None = None
    amount: Decimal
    paid_on: date
    method: PaymentMethod
    reference: str | None
    notes: str | None
    created_at: datetime


class ClientReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str | None = None
    amount: Decimal
    received_on: date
    method: PaymentMethod
    reference: str | None
    notes: str | None
    created_at: datetime


class ProjectCash(BaseModel):
    project_id: uuid.UUID | None  # None: purchase orders not tied to a project
    project_name: str
    received: Decimal
    paid_out: Decimal
    net: Decimal


class SupplierPayable(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    committed: Decimal  # approved-or-later PO value
    paid: Decimal
    outstanding: Decimal


class CashSummary(BaseModel):
    total_received: Decimal
    total_paid_out: Decimal
    net: Decimal
    total_outstanding: Decimal
    projects: list[ProjectCash]
    payables: list[SupplierPayable]
