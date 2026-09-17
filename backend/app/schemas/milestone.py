import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MilestoneBase(BaseModel):
    name: str
    due_date: date | None = None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    name: str | None = None
    due_date: date | None = None
    is_completed: bool | None = None
    completed_date: date | None = None


class MilestoneRead(MilestoneBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    is_completed: bool
    completed_date: date | None
    created_at: datetime
    updated_at: datetime
