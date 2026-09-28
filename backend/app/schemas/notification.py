import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    notification_type: NotificationType
    title: str
    body: str | None
    link: str | None
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    unread_count: int
