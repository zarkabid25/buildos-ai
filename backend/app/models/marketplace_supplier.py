import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TimestampedBase
from app.models.enums import MarketplaceSupplierStatus


class MarketplaceSupplier(TimestampedBase):
    """A supplier organization in BuildOS's own global registry -- shared across
    every construction company, unlike the existing per-company `Supplier` model
    (app/models/supplier.py), which stays exactly as it is and is never touched
    or read by this module. A MarketplaceSupplier has no login of its own yet
    (PLAT-016..020 is admin-managed only); that's deliberately out of scope here,
    see docs/tickets.md Epic 27."""

    __tablename__ = "marketplace_suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[MarketplaceSupplierStatus] = mapped_column(
        Enum(MarketplaceSupplierStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=MarketplaceSupplierStatus.PENDING,
        index=True,
        nullable=False,
    )
    onboarded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)

    contacts: Mapped[list["MarketplaceSupplierContact"]] = relationship(
        cascade="all, delete-orphan", order_by="MarketplaceSupplierContact.created_at"
    )
    documents: Mapped[list["MarketplaceSupplierDocument"]] = relationship(
        cascade="all, delete-orphan", order_by="MarketplaceSupplierDocument.created_at.desc()"
    )
    categories: Mapped[list["MarketplaceSupplierCategory"]] = relationship(cascade="all, delete-orphan")
    coverage_areas: Mapped[list["MarketplaceSupplierCoverageArea"]] = relationship(cascade="all, delete-orphan")
    products: Mapped[list["MarketplaceProduct"]] = relationship(order_by="MarketplaceProduct.created_at.desc()")


class MarketplaceSupplierContact(TimestampedBase):
    __tablename__ = "marketplace_supplier_contacts"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MarketplaceSupplierDocument(TimestampedBase):
    """Verification documents (certificates, licenses, etc.) -- same storage
    backend as the tenant Document model (app/core/storage.py), namespaced by
    supplier id instead of company id. No text extraction/search here; this is
    purely for a human reviewer during verification."""

    __tablename__ = "marketplace_supplier_documents"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)


class MarketplaceSupplierCategory(TimestampedBase):
    """A material/trade category this supplier deals in (e.g. "cement",
    "steel", "electrical"). Free text, not an enum -- the marketplace's category
    vocabulary isn't fixed yet, and a plain join table avoids a migration every
    time a new one is needed."""

    __tablename__ = "marketplace_supplier_categories"
    __table_args__ = (UniqueConstraint("supplier_id", "category", name="uq_marketplace_supplier_category"),)

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)


class MarketplaceSupplierCoverageArea(TimestampedBase):
    """A region/area this supplier delivers to. Same free-text-tag approach as
    categories."""

    __tablename__ = "marketplace_supplier_coverage_areas"
    __table_args__ = (UniqueConstraint("supplier_id", "area", name="uq_marketplace_supplier_coverage_area"),)

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    area: Mapped[str] = mapped_column(String(100), nullable=False)


class MarketplaceProduct(TimestampedBase):
    """One catalog line a marketplace supplier offers (PLAT-019): what, at what
    price, minimum order quantity and lead time. Entered by platform staff on
    the supplier's behalf, same as how tenant staff enter quotations today --
    the supplier has no login to enter this themselves yet."""

    __tablename__ = "marketplace_products"

    supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    minimum_order_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=1, nullable=False)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MarketplaceCompanySupplierLink(TimestampedBase):
    """A tenant company connected to a marketplace supplier (PLAT-022). As of
    migration 0026 this is read by the marketplace integration: `erp_supplier_id`
    is the row in *that company's own* `suppliers` table that RFQs/quotations
    actually reference (RfqSupplier/Quotation FK the tenant Supplier, never a
    MarketplaceSupplier directly) -- either linked to an existing one or created
    fresh through the existing `supplier_service.create_supplier`, never a new
    supplier system. Either a platform staff member or the company's own user
    can create the connection; exactly one of `linked_by_id`/`linked_by_user_id`
    is set."""

    __tablename__ = "marketplace_company_supplier_links"
    __table_args__ = (UniqueConstraint("company_id", "marketplace_supplier_id", name="uq_company_marketplace_supplier"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    erp_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True
    )
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    linked_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    linked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class MarketplaceMaterialMapping(TimestampedBase):
    """Groundwork for future integration (PLAT-020): links a tenant's own
    Material to a marketplace catalog product, so a future RFQ/PO flow could
    one day pull marketplace pricing against a company's existing material
    records. Nothing reads this yet either."""

    __tablename__ = "marketplace_material_mappings"
    __table_args__ = (
        UniqueConstraint("company_id", "material_id", "marketplace_product_id", name="uq_material_mapping"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), index=True, nullable=False)
    marketplace_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_products.id"), index=True, nullable=False
    )
    mapped_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)


class MarketplaceRfqInvitation(TimestampedBase):
    """A marketplace supplier invited to quote on a company's existing ERP RFQ
    (PLAT-023). This never replaces RfqSupplier -- inviting a connected
    marketplace supplier also creates the normal RfqSupplier row through the
    existing rfq flow, using the link's erp_supplier_id. This table is purely
    the marketplace-side invitation record and status tracker. The unique
    constraint is what actually prevents a duplicate invitation, not just an
    application-level check."""

    __tablename__ = "marketplace_rfq_invitations"
    __table_args__ = (UniqueConstraint("rfq_id", "marketplace_supplier_id", name="uq_rfq_marketplace_supplier"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfqs.id"), index=True, nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="invited", nullable=False)  # invited, quoted, declined
    invited_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class MarketplaceDeliveryReport(TimestampedBase):
    """A supplier-claimed delivery event against a real ERP purchase order
    (PLAT-026). Deliberately inert: recording one never touches
    InventoryTransaction or PurchaseOrderItem.quantity_received -- actual stock
    only ever moves through the existing procurement_service.create_goods_receipt.
    `external_reference` makes reporting idempotent: reporting the same event
    twice (e.g. a retried webhook) returns the existing row instead of a
    duplicate."""

    __tablename__ = "marketplace_delivery_reports"
    __table_args__ = (UniqueConstraint("purchase_order_id", "external_reference", name="uq_delivery_report_reference"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=False)
    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), index=True, nullable=False
    )
    external_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reported_by_staff_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
