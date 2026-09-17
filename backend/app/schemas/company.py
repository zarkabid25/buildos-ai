import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CompanyBase(BaseModel):
    name: str
    code: str
    currency: str = "PKR"
    unit_system: str = "metric"
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    currency: str | None = None
    unit_system: str | None = None
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    logo_url: str | None = None
    created_at: datetime
    updated_at: datetime
