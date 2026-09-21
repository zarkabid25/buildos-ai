import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ExpenseCategoryRead(ExpenseCategoryCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class ExpenseCreate(BaseModel):
    project_id: uuid.UUID
    category_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0)
    description: str | None = None
    expense_date: date


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    category_id: uuid.UUID | None
    amount: Decimal
    description: str | None
    expense_date: date
    created_by_id: uuid.UUID
    created_at: datetime


class ProjectCostSummary(BaseModel):
    original_budget: Decimal
    committed: Decimal
    actual: Decimal
    remaining: Decimal
    forecast: Decimal
    expected_variance: Decimal
    forecast_basis: str
