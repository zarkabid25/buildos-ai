import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MarketplaceSupplierStatus, SupplierMembershipRole, SupplierMembershipStatus


# ---- PLAT-038: auth, memberships, invitations ------------------------------------------------


class SupplierLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SupplierMembershipSummary(BaseModel):
    marketplace_supplier_id: uuid.UUID
    marketplace_supplier_name: str
    role: SupplierMembershipRole
    status: SupplierMembershipStatus


class SupplierTokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    active_supplier_id: uuid.UUID | None  # null when the caller must pick one (multi-membership login)


class SupplierUserRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool

    model_config = {"from_attributes": True}


class SupplierAuthResponse(SupplierTokenPair):
    user: SupplierUserRead
    memberships: list[SupplierMembershipSummary]


class SupplierSelectSupplierRequest(BaseModel):
    refresh_token: str
    marketplace_supplier_id: uuid.UUID


class SupplierRefreshRequest(BaseModel):
    refresh_token: str


class SupplierInvitationCreate(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)
    role: SupplierMembershipRole = SupplierMembershipRole.STAFF


class SupplierInvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: SupplierMembershipRole
    invited_by_name: str | None
    created_at: datetime
    expires_at: datetime
    expired: bool


class SupplierInvitationCreated(SupplierInvitationRead):
    token: str  # shown once


class SupplierInvitationInfo(BaseModel):
    """Public, pre-auth lookup shown on the accept-invite page."""

    marketplace_supplier_name: str
    email: str
    full_name: str | None
    role: SupplierMembershipRole


class SupplierAcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class SupplierMembershipRead(BaseModel):
    id: uuid.UUID
    supplier_user_id: uuid.UUID
    user_full_name: str
    user_email: str
    role: SupplierMembershipRole
    status: SupplierMembershipStatus
    created_at: datetime


class SupplierMembershipRoleUpdate(BaseModel):
    role: SupplierMembershipRole


# ---- PLAT-039: dashboard and profile ----------------------------------------------------------


class SupplierDashboard(BaseModel):
    new_invitations: int
    pending_quotations: int  # invited, not yet quoted or declined
    submitted_quotations: int
    active_linked_orders: int
    pending_delivery_updates: int  # active orders with no delivery report yet
    outstanding_commission_invoices: int


class SupplierProfileRead(BaseModel):
    id: uuid.UUID
    name: str
    legal_name: str | None
    email: str | None
    phone: str | None
    website: str | None
    address: str | None
    notes: str | None
    verification_status: MarketplaceSupplierStatus
    categories: list[str]
    coverage_areas: list[str]


class SupplierProfileUpdate(BaseModel):
    """Deliberately narrower than the platform-admin MarketplaceSupplierUpdate:
    name/legal_name/verification_status are never editable here -- those stay
    on the existing staff approval workflow (PLAT-018), so a supplier can
    never self-approve its own verification or silently rebrand itself."""

    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    notes: str | None = None
    categories: list[str] | None = None
    coverage_areas: list[str] | None = None


class SupplierDocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---- PLAT-040: product catalog ------------------------------------------------------------------


class SupplierProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=50)
    price: Decimal = Field(gt=0)
    minimum_order_quantity: Decimal = Field(default=Decimal(1), gt=0)
    lead_time_days: int | None = Field(default=None, ge=0)


class SupplierProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=50)
    price: Decimal | None = Field(default=None, gt=0)
    minimum_order_quantity: Decimal | None = Field(default=None, gt=0)
    lead_time_days: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class SupplierProductRead(BaseModel):
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


# ---- PLAT-041: RFQ inbox and quotations ----------------------------------------------------------


class SupplierRfqInboxItem(BaseModel):
    invitation_id: uuid.UUID
    rfq_id: uuid.UUID
    rfq_number: str
    title: str
    company_name: str
    status: str  # invited / quoted / declined
    response_due: date | None
    created_at: datetime


class SupplierRfqItemRead(BaseModel):
    id: uuid.UUID
    material_name: str
    unit: str
    quantity: Decimal


class SupplierOwnQuotationItem(BaseModel):
    rfq_item_id: uuid.UUID
    rate: Decimal
    amount: Decimal


class SupplierOwnQuotation(BaseModel):
    id: uuid.UUID
    delivery_days: int | None
    valid_until: date | None
    notes: str | None
    total: Decimal
    created_at: datetime
    items: list[SupplierOwnQuotationItem]


class SupplierRfqDetail(BaseModel):
    """Never includes other suppliers' invitations or quotations -- only this
    RFQ's own requirements and the caller's own invitation/quotation state."""

    rfq_id: uuid.UUID
    rfq_number: str
    title: str
    company_name: str
    notes: str | None
    response_due: date | None
    rfq_status: str
    invitation_status: str
    items: list[SupplierRfqItemRead]
    my_quotation: SupplierOwnQuotation | None


class SupplierQuotationItemInput(BaseModel):
    rfq_item_id: uuid.UUID
    rate: Decimal = Field(ge=0)


class SupplierQuotationSubmit(BaseModel):
    delivery_days: int | None = Field(default=None, ge=0, le=3650)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    items: list[SupplierQuotationItemInput] = Field(min_length=1)


class SupplierQuotationHistoryItem(BaseModel):
    rfq_id: uuid.UUID
    rfq_number: str
    company_name: str
    total: Decimal
    submitted_at: datetime


# ---- PLAT-042: orders, delivery, commission statements ---------------------------------------------


class SupplierOrderItemRead(BaseModel):
    id: uuid.UUID
    material_name: str
    quantity: Decimal
    rate: Decimal
    quantity_received: Decimal
    amount: Decimal


class SupplierOrderRead(BaseModel):
    purchase_order_id: uuid.UUID
    po_number: str
    company_name: str
    status: str
    total_amount: Decimal
    amount_paid: Decimal
    created_at: datetime
    items: list[SupplierOrderItemRead]


class SupplierDeliveryUpdateCreate(BaseModel):
    external_reference: str = Field(min_length=1, max_length=100)
    note: str | None = Field(default=None, max_length=500)


class SupplierDeliveryUpdateRead(BaseModel):
    id: uuid.UUID
    purchase_order_id: uuid.UUID
    external_reference: str
    note: str | None
    created_at: datetime
    already_recorded: bool = False

    model_config = {"from_attributes": True}
