import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttendanceStatus


class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    designation: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    daily_wage: Decimal = Field(default=Decimal("0"), ge=0)
    hire_date: date | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    designation: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    daily_wage: Decimal | None = Field(default=None, ge=0)
    hire_date: date | None = None
    is_active: bool | None = None


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    designation: str | None
    phone: str | None
    email: str | None
    daily_wage: Decimal
    hire_date: date | None
    is_active: bool
    created_at: datetime


class EmployeeAssignmentCreate(BaseModel):
    project_id: uuid.UUID


class EmployeeAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    project_id: uuid.UUID


class AttendanceCreate(BaseModel):
    employee_id: uuid.UUID
    project_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus = AttendanceStatus.PRESENT


class AttendanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    project_id: uuid.UUID
    attendance_date: date
    status: AttendanceStatus


class ProjectLaborCost(BaseModel):
    project_id: uuid.UUID
    total_labor_cost: Decimal
    present_days: int
    half_days: int
    employee_count: int


class EmployeeProductivity(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    total_days_recorded: int
    present_days: int
    absent_days: int
    attendance_rate_percent: Decimal
