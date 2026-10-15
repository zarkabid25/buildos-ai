import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MarketplaceSupplierStatus


class MarketplaceSupplierContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_primary: bool = False


class MarketplaceSupplierContactRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    name: str
    role: str | None
    email: str | None
    phone: str | None
    is_primary: bool

    model_config = {"from_attributes": True}


class MarketplaceSupplierDocumentRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0)
    minimum_order_quantity: Decimal = Field(default=Decimal(1), gt=0)
    lead_time_days: int | None = Field(default=None, ge=0)


class MarketplaceProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    price: Decimal | None = Field(default=None, gt=0)
    minimum_order_quantity: Decimal | None = Field(default=None, gt=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class MarketplaceProductRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    name: str
    category: str | None
    unit: str
    price: Decimal
    minimum_order_quantity: Decimal
    lead_time_days: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceSupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    categories: list[str] = Field(default_factory=list)
    coverage_areas: list[str] = Field(default_factory=list)


class MarketplaceSupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    categories: list[str] | None = None
    coverage_areas: list[str] | None = None


class MarketplaceSupplierRead(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    notes: str | None
    verification_status: MarketplaceSupplierStatus
    onboarded_by_id: uuid.UUID
    onboarded_by_name: str | None = None
    categories: list[str]
    coverage_areas: list[str]
    created_at: datetime
    updated_at: datetime


class MarketplaceSupplierCreated(BaseModel):
    supplier: MarketplaceSupplierRead
    # Never auto-merged -- the new record is always created. These are just a
    # heads-up for the staff member who created it, to review by hand.
    possible_duplicates: list[MarketplaceSupplierRead]


class MarketplaceSupplierDetail(MarketplaceSupplierRead):
    contacts: list[MarketplaceSupplierContactRead]
    documents: list[MarketplaceSupplierDocumentRead]
    products: list[MarketplaceProductRead]


class MarketplaceSupplierList(BaseModel):
    total: int
    suppliers: list[MarketplaceSupplierRead]


class MarketplaceVerificationUpdate(BaseModel):
    status: MarketplaceSupplierStatus
    reason: str | None = Field(default=None, max_length=500)


class MarketplaceCompanyLinkCreate(BaseModel):
    company_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=500)


class MarketplaceCompanyLinkRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    company_name: str | None = None
    marketplace_supplier_id: uuid.UUID
    erp_supplier_id: uuid.UUID | None = None
    is_preferred: bool = False
    status: str = "active"
    linked_by_id: uuid.UUID | None
    linked_by_user_id: uuid.UUID | None = None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceMaterialMappingCreate(BaseModel):
    company_id: uuid.UUID
    material_id: uuid.UUID
    marketplace_product_id: uuid.UUID


class MarketplaceMaterialMappingRead(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    material_id: uuid.UUID
    marketplace_product_id: uuid.UUID
    mapped_by_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
