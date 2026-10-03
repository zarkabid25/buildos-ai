import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID
    actor_name: str | None = None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    summary: str
    details: dict[str, Any] | None
