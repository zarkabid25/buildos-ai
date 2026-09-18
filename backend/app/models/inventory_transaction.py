import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase
from app.models.enums import InventoryTransactionType


class InventoryTransaction(TenantBase):
    """Append-only movement ledger. Current stock on hand is derived by summing
    these rows (IN types add, OUT types subtract) rather than stored as a mutable
    balance column, so the balance can never drift out of sync with its history."""

    __tablename__ = "inventory_transactions"

    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), index=True, nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    transaction_type: Mapped[InventoryTransactionType] = mapped_column(
        Enum(
            InventoryTransactionType,
            name="inventory_transaction_type",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    # Links the two rows of a single transfer (TRANSFER_OUT + TRANSFER_IN) together.
    transfer_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
