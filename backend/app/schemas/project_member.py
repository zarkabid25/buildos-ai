import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class ProjectMemberAdd(BaseModel):
    user_id: uuid.UUID


class ProjectMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime


class ProjectMemberWithUser(ProjectMemberRead):
    user: UserRead
