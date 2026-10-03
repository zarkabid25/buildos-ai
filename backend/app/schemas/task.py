import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    start_date: date | None = None
    due_date: date | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority | None = None
    status: TaskStatus | None = None
    start_date: date | None = None
    due_date: date | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    depends_on: list[uuid.UUID] = Field(default_factory=list)


class CompanyTaskRead(TaskRead):
    """A task in the company-wide list, with enough context to show it outside its project."""

    project_name: str
    project_code: str
    assignee_name: str | None = None


class TaskDependencyCreate(BaseModel):
    depends_on_task_id: uuid.UUID


class ScheduleMilestone(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    due_date: date | None
    is_completed: bool


class ProjectSchedule(BaseModel):
    tasks: list[TaskRead]
    milestones: list[ScheduleMilestone]
    schedule_variance_percent: int | None
    schedule_variance_days: int | None
    variance_note: str
