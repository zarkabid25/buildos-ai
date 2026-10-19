import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import SupplierApplicationStatus


# ---- PLAT-044: demo requests ------------------------------------------------------------------


class DemoRequestCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    company_name: str = Field(min_length=2, max_length=255)
    message: str | None = Field(default=None, max_length=2000)


class DemoRequestRead(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    company_name: str
    message: str | None
    crm_organization_id: uuid.UUID | None
    already_submitted: bool = False
    created_at: datetime


# ---- PLAT-045: supplier applications -----------------------------------------------------------


class SupplierApplicationCreate(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    contact_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    business_registration_info: str | None = Field(default=None, max_length=500)
    categories: list[str] = Field(default_factory=list, max_length=500)
    delivery_locations: list[str] = Field(default_factory=list, max_length=500)
    business_description: str | None = Field(default=None, max_length=2000)


class SupplierApplicationRead(BaseModel):
    id: uuid.UUID
    business_name: str
    contact_name: str
    email: str
    phone: str | None
    business_registration_info: str | None
    categories: list[str]
    delivery_locations: list[str]
    business_description: str | None
    status: SupplierApplicationStatus
    review_notes: str | None
    reviewed_by_staff_id: uuid.UUID | None
    reviewed_by_staff_name: str | None = None
    reviewed_at: datetime | None
    marketplace_supplier_id: uuid.UUID | None
    document_count: int = 0
    created_at: datetime


class SupplierApplicationReview(BaseModel):
    approve: bool
    review_notes: str = Field(min_length=1, max_length=1000)


class SupplierApplicationDocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
