import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BoqItemBase(BaseModel):
    item_code: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Decimal("0")
    rate: Decimal = Decimal("0")
    material_id: uuid.UUID | None = None


class BoqItemCreate(BoqItemBase):
    pass


class BoqItemUpdate(BaseModel):
    item_code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=20)
    quantity: Decimal | None = None
    rate: Decimal | None = None
    material_id: uuid.UUID | None = None


class BoqItemRead(BoqItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    amount: Decimal
    is_ai_generated: bool
    created_at: datetime
    updated_at: datetime


class BoqCategoryTotal(BaseModel):
    category: str
    total_amount: Decimal
    item_count: int


class BoqSummary(BaseModel):
    total_amount: Decimal
    item_count: int
    by_category: list[BoqCategoryTotal]


BoqLineStatus = Literal["not_tracked", "not_started", "within_plan", "over_plan"]


class BoqVsActualLine(BaseModel):
    boq_item_id: uuid.UUID
    item_code: str
    description: str
    unit: str
    material_id: uuid.UUID | None
    material_name: str | None
    planned_quantity: Decimal
    rate: Decimal
    planned_amount: Decimal
    # None when the line isn't linked to a material, i.e. there is nothing to measure.
    actual_quantity: Decimal | None
    actual_amount: Decimal | None
    quantity_variance: Decimal | None
    variance_percent: Decimal | None
    status: BoqLineStatus


class UnplannedConsumption(BaseModel):
    material_id: uuid.UUID
    material_name: str
    unit: str
    actual_quantity: Decimal


class BoqVsActual(BaseModel):
    lines: list[BoqVsActualLine]
    # Materials allocated to the project that no BOQ line is linked to.
    unplanned: list[UnplannedConsumption]
    planned_total: Decimal
    tracked_planned_total: Decimal
    actual_total: Decimal
    valuation_note: str = (
        "Actual quantity is stock allocated to this project from inventory. Actual amount "
        "values that quantity at the BOQ rate, so the variance shown is a quantity variance, "
        "not a price variance."
    )


class BoqAiGenerateRequest(BaseModel):
    project_type: str = Field(min_length=2, description="e.g. 'residential', '10000 sq ft house'")
    notes: str | None = None


class BoqAiGeneratedItem(BaseModel):
    item_code: str
    description: str
    category: str
    unit: str
    quantity: Decimal
    rate: Decimal


class BoqAiGenerateResponse(BaseModel):
    items: list[BoqAiGeneratedItem]
    disclaimer: str = (
        "These quantities and rates are AI-generated estimates and must be reviewed "
        "by a qualified quantity surveyor or engineer before use."
    )
