import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyReportCreate(BaseModel):
    report_date: date
    weather: str | None = None
    workers_count: int = Field(default=0, ge=0)
    work_completed: str | None = None
    materials_consumed: str | None = None
    equipment_used: str | None = None
    problems: str | None = None
    notes: str | None = None


class DailyReportPhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    content_type: str
    size_bytes: int


class DailyReportRead(DailyReportCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    created_by_id: uuid.UUID
    created_at: datetime
    photos: list[DailyReportPhotoRead]
