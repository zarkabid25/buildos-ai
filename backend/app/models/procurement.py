import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TenantBase
from app.models.enums import MaterialRequestStatus, PurchaseOrderStatus


class MaterialRequest(TenantBase):
    __tablename__ = "material_requests"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[MaterialRequestStatus] = mapped_column(
        Enum(
            MaterialRequestStatus,
            name="material_request_status",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        default=MaterialRequestStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    items: Mapped[list["MaterialRequestItem"]] = relationship()


class MaterialRequestItem(TenantBase):
    __tablename__ = "material_request_items"

    material_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_requests.id"), index=True, nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)


class PurchaseOrder(TenantBase):
    __tablename__ = "purchase_orders"

    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    material_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("material_requests.id"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(
            PurchaseOrderStatus,
            name="purchase_order_status",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        default=PurchaseOrderStatus.DRAFT,
        nullable=False,
    )
    po_number: Mapped[str] = mapped_column(String(50), nullable=False)

    items: Mapped[list["PurchaseOrderItem"]] = relationship()

    @property
    def total_amount(self) -> Decimal:
        return sum((item.amount for item in self.items), Decimal("0"))


class PurchaseOrderItem(TenantBase):
    __tablename__ = "purchase_order_items"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), index=True, nullable=False
    )
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False, default=0)

    @property
    def amount(self) -> Decimal:
        return (self.quantity or Decimal("0")) * (self.rate or Decimal("0"))


class GoodsReceipt(TenantBase):
    __tablename__ = "goods_receipts"

    purchase_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_orders.id"), index=True, nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("warehouses.id"))
    received_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    items: Mapped[list["GoodsReceiptItem"]] = relationship()


class GoodsReceiptItem(TenantBase):
    __tablename__ = "goods_receipt_items"

    goods_receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goods_receipts.id"), index=True, nullable=False
    )
    purchase_order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_items.id")
    )
    material_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.id"))
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
