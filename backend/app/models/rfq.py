import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TenantBase
from app.models.enums import RfqStatus


class Rfq(TenantBase):
    """Request for quotation (BUILD-041): what we want priced, and by whom."""

    __tablename__ = "rfqs"

    rfq_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=True
    )
    material_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_requests.id"), nullable=True
    )
    response_due: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Stored as text (not a Postgres enum) so adding a status needs no migration.
    status: Mapped[RfqStatus] = mapped_column(
        Enum(RfqStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=RfqStatus.OPEN,
        nullable=False,
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    awarded_quotation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    purchase_order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True
    )

    items: Mapped[list["RfqItem"]] = relationship(order_by="RfqItem.created_at")
    invited: Mapped[list["RfqSupplier"]] = relationship()
    quotations: Mapped[list["Quotation"]] = relationship()


class RfqItem(TenantBase):
    __tablename__ = "rfq_items"

    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfqs.id"), index=True, nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)


class RfqSupplier(TenantBase):
    """A supplier asked to quote on an RFQ."""

    __tablename__ = "rfq_suppliers"
    __table_args__ = (UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_supplier"),)

    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfqs.id"), index=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)


class Quotation(TenantBase):
    """One supplier's priced answer to an RFQ (BUILD-042). Entered by staff;
    suppliers don't log in. One per supplier per RFQ; re-entering replaces it."""

    __tablename__ = "quotations"
    __table_args__ = (UniqueConstraint("rfq_id", "supplier_id", name="uq_quotation_supplier"),)

    rfq_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfqs.id"), index=True, nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    delivery_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    items: Mapped[list["QuotationItem"]] = relationship(cascade="all, delete-orphan")


class QuotationItem(TenantBase):
    __tablename__ = "quotation_items"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quotations.id"), index=True, nullable=False
    )
    rfq_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rfq_items.id"), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
