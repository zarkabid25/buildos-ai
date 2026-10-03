import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WarehouseBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)


class WarehouseRead(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
