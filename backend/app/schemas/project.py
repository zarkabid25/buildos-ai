import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectStatus


class ProjectBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    client_name: str | None = None
    location: str | None = None
    project_type: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal = Decimal("0")


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    location: str | None = None
    project_type: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    budget: Decimal | None = None
    status: ProjectStatus | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)


class ProjectRead(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    status: ProjectStatus
    progress_percent: int
    created_by_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProjectSummary(BaseModel):
    total_projects: int
    total_budget: Decimal
    avg_progress: float
    at_risk_count: int
