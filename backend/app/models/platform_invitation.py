import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase
from app.models.enums import PlatformStaffRole


class PlatformInvitation(TimestampedBase):
    """An owner's invitation for a new platform staff member (PLAT-010). Mirrors
    the tenant Invitation model: only a SHA-256 hash of the token is stored."""

    __tablename__ = "platform_invitations"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[PlatformStaffRole] = mapped_column(
        Enum(PlatformStaffRole, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False
    )
