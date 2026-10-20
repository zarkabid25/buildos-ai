"""Phase 8 notification extensions. The existing Notification model
(app/models/notification.py) is tenant-only (TenantBase: company_id + user_id
required) -- there was no platform-staff or supplier-user notification
concept before Phase 8. Rather than redesign that table to be polymorphic,
these mirror its shape for the other two actor types, same convention as
audit logging already having a separate tenant/platform mechanism.

EmailDeliveryLog is the honest record PLAT-047 asked for: this app has no
SMTP/SES/SendGrid configured anywhere (confirmed before writing this), so
every row here is expected to land as NOT_CONFIGURED, never a pretended
SENT."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase
from app.models.enums import EmailDeliveryStatus


class SupplierNotification(TimestampedBase):
    __tablename__ = "supplier_notifications"

    supplier_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_users.id"), index=True, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PlatformNotification(TimestampedBase):
    """A shared feed visible to all platform staff (demo requests, supplier
    applications, new support tickets) -- not per-staff read state, same
    simplification already implicit in PlatformAuditLog being a shared,
    global log rather than per-viewer."""

    __tablename__ = "platform_notifications"

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(String(500), nullable=True)
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailDeliveryLog(TimestampedBase):
    __tablename__ = "email_delivery_logs"
    __table_args__ = (
        # Phase 9.1 (Task 3): lets send_templated() detect "this exact
        # notification was already sent" and skip resending on a retried
        # request, without the caller needing its own dedup bookkeeping.
        UniqueConstraint("dedup_key", name="uq_email_delivery_logs_dedup_key"),
    )

    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EmailDeliveryStatus] = mapped_column(
        Enum(EmailDeliveryStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), index=True, nullable=False
    )
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    template_key: Mapped[str | None] = mapped_column(String(50), nullable=True)
    dedup_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
