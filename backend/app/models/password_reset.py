"""Phase 9.1 (Task 3): "forgot password" for the tenant auth system --
previously there was no self-service path to reset a password at all, only
the authenticated /auth/me/password change. Mirrors the existing
Invitation/SupplierInvitation token mechanics (secrets.token_urlsafe(32) +
SHA-256 hash, single use, short expiry) rather than inventing a new pattern."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase


class PasswordResetToken(TimestampedBase):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
