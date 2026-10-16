import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import MarketplaceSupplierStatus


# ---- PLAT-021 Company-facing supplier discovery (read-only, verified only) -----------


class DiscoverySupplierRead(BaseModel):
    id: uuid.UUID
    name: str
    categories: list[str]
    coverage_areas: list[str]
    verification_status: MarketplaceSupplierStatus
    is_connected: bool
    is_preferred: bool

    model_config = {"from_attributes": True}


class DiscoveryProductRead(BaseModel):
    id: uuid.UUID
    name: str
    category: str | None
    unit: str
    price: Decimal
    minimum_order_quantity: Decimal
    lead_time_days: int | None

    model_config = {"from_attributes": True}


class DiscoverySupplierDetail(DiscoverySupplierRead):
    products: list[DiscoveryProductRead]


# ---- PLAT-022 Company-supplier relationships -------------------------------------------


class ConnectSupplierRequest(BaseModel):
    """Exactly one of the two: link an ERP supplier the company already has, or
    create a new one (through the existing supplier_service) seeded from the
    marketplace supplier's details."""

    link_existing_erp_supplier_id: uuid.UUID | None = None
    create_new_erp_supplier: bool = False
    is_preferred: bool = False
    notes: str | None = Field(default=None, max_length=500)


class CompanySupplierConnectionRead(BaseModel):
    id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str | None = None
    erp_supplier_id: uuid.UUID | None
    is_preferred: bool
    status: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateConnectionRequest(BaseModel):
    is_preferred: bool | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


# ---- PLAT-023 Marketplace RFQ invitations -----------------------------------------------


class InviteSuppliersRequest(BaseModel):
    marketplace_supplier_ids: list[uuid.UUID] = Field(min_length=1)


class AssistedQuotationItemInput(BaseModel):
    rfq_item_id: uuid.UUID
    rate: Decimal = Field(ge=0)


class AssistedQuotationCreate(BaseModel):
    """Same shape as the real QuotationCreate, minus supplier_id -- the server
    resolves that from the company's connection to this marketplace supplier,
    so platform staff can't accidentally (or otherwise) submit a quotation
    against a different supplier than the one they're assisting."""

    delivery_days: int | None = Field(default=None, ge=0, le=3650)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[AssistedQuotationItemInput] = Field(min_length=1)


class MarketplaceInvitationRead(BaseModel):
    id: uuid.UUID
    rfq_id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str | None = None
    status: str
    invited_by_staff_id: uuid.UUID | None
    invited_by_user_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- PLAT-025/026 purchase order + delivery reporting ------------------------------------


class MarketplaceOrderStatus(BaseModel):
    """Derived entirely from real ERP data -- never a separately-tracked status
    that could drift from the truth."""

    purchase_order_id: uuid.UUID
    po_number: str
    status: str  # the real PurchaseOrder.status
    total_amount: Decimal
    amount_paid: Decimal
    goods_receipt_count: int
    fully_received: bool
    delivery_reported: bool
    last_delivery_report_at: datetime | None


class DeliveryReportCreate(BaseModel):
    external_reference: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)


class DeliveryReportRead(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    external_reference: str
    note: str | None
    reported_by_staff_id: uuid.UUID
    created_at: datetime
    already_recorded: bool = False

    model_config = {"from_attributes": True}


# ---- PLAT-027 Platform-assisted supplier matching ----------------------------------------


class SupplierMatch(BaseModel):
    marketplace_supplier_id: uuid.UUID
    supplier_name: str
    verification_status: MarketplaceSupplierStatus
    product_id: uuid.UUID
    product_name: str
    price: Decimal
    minimum_order_quantity: Decimal
    lead_time_days: int | None
    coverage_areas: list[str]
    matched_via: str  # "material_mapping" or "category"


# ---- Phase 4.1 Task 3: immutable quotation attribution -----------------------------------


class QuotationAttributionRead(BaseModel):
    id: uuid.UUID
    quotation_id: uuid.UUID
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str
    submitted_by_staff_id: uuid.UUID
    submitted_by_staff_name: str
    method: str
    total_amount: Decimal
    created_at: datetime
