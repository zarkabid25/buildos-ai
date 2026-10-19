"""Public website lead capture and supplier applications (Phase 8,
PLAT-044/045). Both are genuinely new concepts -- nothing in this app
previously had an unauthenticated write path at all. Neither auto-creates a
privileged record: a demo request links/creates a CrmOrganization (a lead,
not a tenant) exactly like a staff-entered lead would; a supplier
application stays its own pending-review record until a staff member
explicitly approves it, which only then creates a MarketplaceSupplier --
still PENDING verification, never auto-verified."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase
from app.models.enums import SupplierApplicationStatus


class DemoRequest(TimestampedBase):
    """A public 'request a demo' submission (PLAT-044). Always linked to a
    CrmOrganization (created or reused -- never duplicated) so the existing
    CRM pipeline is the single place sales follows up; this table is the
    raw, literal record of what the visitor actually submitted and is also
    what duplicate-submission protection keys off (same email within the
    rate-limit window reuses the same row instead of creating a new one)."""

    __tablename__ = "demo_requests"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    crm_organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("crm_organizations.id"), nullable=True)


class SupplierApplication(TimestampedBase):
    """A public 'become a supplier' submission (PLAT-045). Deliberately a
    separate table from MarketplaceSupplier, not a direct write into it:
    MarketplaceSupplier.onboarded_by_id is a required FK to a real
    PlatformAdmin, which an anonymous public submission can never satisfy.
    Approving an application calls the existing, unmodified
    marketplace_supplier_service.create_supplier with the approving staff
    member as the real actor -- the resulting supplier still starts PENDING
    verification like every other supplier ever onboarded; approval of the
    *application* and verification of the *supplier* stay two separate,
    both staff-gated steps."""

    __tablename__ = "supplier_applications"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    business_registration_info: Mapped[str | None] = mapped_column(String(500), nullable=True)
    categories: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated, free text
    delivery_locations: Mapped[str | None] = mapped_column(String(500), nullable=True)  # comma-separated, free text
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SupplierApplicationStatus] = mapped_column(
        Enum(SupplierApplicationStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=SupplierApplicationStatus.PENDING, index=True, nullable=False,
    )
    review_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    reviewed_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketplace_supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), nullable=True)


class SupplierApplicationDocument(TimestampedBase):
    """Optional supporting documents (registration certificate, etc.), same
    private-storage backend as every other upload in this app."""

    __tablename__ = "supplier_application_documents"

    application_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_applications.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
