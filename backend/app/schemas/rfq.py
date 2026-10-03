import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import RfqStatus


class RfqItemInput(BaseModel):
    material_id: uuid.UUID
    quantity: Decimal = Field(gt=0)


class RfqCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    project_id: uuid.UUID | None = None
    # Raising an RFQ from a material request copies its items when none are given.
    material_request_id: uuid.UUID | None = None
    response_due: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[RfqItemInput] = Field(default_factory=list)
    supplier_ids: list[uuid.UUID] = Field(default_factory=list)


class QuotationItemInput(BaseModel):
    rfq_item_id: uuid.UUID
    rate: Decimal = Field(ge=0)


class QuotationCreate(BaseModel):
    supplier_id: uuid.UUID
    delivery_days: int | None = Field(default=None, ge=0, le=3650)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[QuotationItemInput] = Field(min_length=1)


class AwardRequest(BaseModel):
    quotation_id: uuid.UUID


class RfqItemRead(BaseModel):
    id: uuid.UUID
    material_id: uuid.UUID
    material_name: str
    unit: str
    quantity: Decimal


class QuotationItemRead(BaseModel):
    rfq_item_id: uuid.UUID
    rate: Decimal
    amount: Decimal
    is_lowest: bool  # cheapest rate for this item among all quotations


class QuotationRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    supplier_name: str
    delivery_days: int | None
    valid_until: date | None
    expired: bool
    notes: str | None
    total: Decimal
    is_lowest_total: bool
    created_at: datetime
    items: list[QuotationItemRead]


class InvitedSupplier(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    has_quoted: bool


class RfqRead(BaseModel):
    """An RFQ with its quotations laid out for comparison (BUILD-043)."""

    id: uuid.UUID
    rfq_number: str
    title: str
    project_id: uuid.UUID | None
    project_name: str | None
    material_request_id: uuid.UUID | None
    response_due: date | None
    notes: str | None
    status: RfqStatus
    created_at: datetime
    items: list[RfqItemRead]
    invited: list[InvitedSupplier]
    quotations: list[QuotationRead]
    awarded_quotation_id: uuid.UUID | None
    purchase_order_id: uuid.UUID | None
    po_number: str | None


class RfqSummary(BaseModel):
    id: uuid.UUID
    rfq_number: str
    title: str
    project_name: str | None
    status: RfqStatus
    response_due: date | None
    item_count: int
    invited_count: int
    quotation_count: int
    lowest_total: Decimal | None
    created_at: datetime
