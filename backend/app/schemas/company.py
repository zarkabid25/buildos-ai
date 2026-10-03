import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CompanyBase(BaseModel):
    name: str = Field(max_length=255)
    code: str = Field(max_length=50)
    currency: str = Field(default="PKR", max_length=10)
    unit_system: str = Field(default="metric", max_length=20)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)
    # ISO 4217 code, e.g. PKR, USD, AED.
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    unit_system: Literal["metric", "imperial"] | None = None
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    logo_url: str | None = None
    created_at: datetime
    updated_at: datetime
