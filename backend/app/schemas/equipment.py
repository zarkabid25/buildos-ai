import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EquipmentStatus


class EquipmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    equipment_type: str | None = None
    notes: str | None = None


class EquipmentUpdate(BaseModel):
    name: str | None = None
    equipment_type: str | None = None
    status: EquipmentStatus | None = None
    current_project_id: uuid.UUID | None = None
    notes: str | None = None


class EquipmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    equipment_type: str | None
    status: EquipmentStatus
    current_project_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class EquipmentMaintenanceCreate(BaseModel):
    maintenance_date: date
    description: str | None = None
    cost: Decimal = Field(default=Decimal("0"), ge=0)
    next_due_date: date | None = None


class EquipmentMaintenanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_id: uuid.UUID
    maintenance_date: date
    description: str | None
    cost: Decimal
    next_due_date: date | None


class MaintenanceReminder(BaseModel):
    equipment_id: uuid.UUID
    equipment_name: str
    next_due_date: date
    days_until_due: int
    is_overdue: bool
