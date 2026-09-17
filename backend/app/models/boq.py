import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase


class BoqItem(TenantBase):
    __tablename__ = "boq_items"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    item_code: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False, default=0)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def amount(self) -> Decimal:
        return (self.quantity or Decimal("0")) * (self.rate or Decimal("0"))
