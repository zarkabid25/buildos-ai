import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialCategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class MaterialCategoryCreate(MaterialCategoryBase):
    pass


class MaterialCategoryRead(MaterialCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class MaterialBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=50)
    unit: str = Field(min_length=1, max_length=20)
    category_id: uuid.UUID | None = None
    reorder_point: int = Field(default=0, ge=0)


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    name: str | None = None
    sku: str | None = None
    unit: str | None = None
    category_id: uuid.UUID | None = None
    reorder_point: int | None = Field(default=None, ge=0)


class MaterialRead(MaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
