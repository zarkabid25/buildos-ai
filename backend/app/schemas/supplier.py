import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SupplierContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class SupplierContactCreate(SupplierContactBase):
    pass


class SupplierContactRead(SupplierContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supplier_id: uuid.UUID
    created_at: datetime
