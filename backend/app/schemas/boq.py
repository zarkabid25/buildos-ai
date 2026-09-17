import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BoqItemBase(BaseModel):
    item_code: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=500)
    category: str | None = None
    unit: str = Field(min_length=1, max_length=20)
    quantity: Decimal = Decimal("0")
    rate: Decimal = Decimal("0")


class BoqItemCreate(BoqItemBase):
    pass


class BoqItemUpdate(BaseModel):
    item_code: str | None = None
    description: str | None = None
    category: str | None = None
    unit: str | None = None
    quantity: Decimal | None = None
    rate: Decimal | None = None


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
