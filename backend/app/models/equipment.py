import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase
from app.models.enums import EquipmentStatus


class Equipment(TenantBase):
    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    equipment_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[EquipmentStatus] = mapped_column(
        Enum(
            EquipmentStatus,
            name="equipment_status",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        default=EquipmentStatus.AVAILABLE,
        nullable=False,
    )
    current_project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EquipmentMaintenance(TenantBase):
    __tablename__ = "equipment_maintenance"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"), index=True, nullable=False
    )
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    next_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
