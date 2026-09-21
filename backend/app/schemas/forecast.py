import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ConsumptionRate(BaseModel):
    material_id: uuid.UUID
    material_name: str
    unit: str
    daily_avg: Decimal
    weekly_avg: Decimal
    monthly_avg: Decimal
    window_days: int


class MaterialForecast(BaseModel):
    material_id: uuid.UUID
    material_name: str
    unit: str
    current_stock: Decimal
    daily_avg_usage: Decimal
    estimated_stockout_date: date | None
    days_remaining: int | None
    recommended_order_quantity: Decimal | None
    reason: str


class MaterialAnomaly(BaseModel):
    material_id: uuid.UUID
    material_name: str
    unit: str
    recent_daily_avg: Decimal
    baseline_daily_avg: Decimal
    change_percent: Decimal
    message: str
