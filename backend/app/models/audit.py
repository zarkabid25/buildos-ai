import uuid

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase


class AuditLog(TenantBase):
    """Append-only record of who did what to money, permissions or data (BUILD-126).
    Rows are only ever inserted; no endpoint updates or deletes them."""

    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # e.g. "purchase_order.approved". A plain string (not a DB enum) so adding an
    # audited action never needs a migration.
    action: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
