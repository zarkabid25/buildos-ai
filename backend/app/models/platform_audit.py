import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase


class PlatformAuditLog(TimestampedBase):
    """Append-only record of platform-staff actions (PLAT-009): company approve/
    suspend/reactivate, staff invited/role changed/deactivated. Deliberately
    separate from the tenant AuditLog -- these actions have no company_id of
    their own (a staff invitation isn't owned by any one company)."""

    __tablename__ = "platform_audit_log"

    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
