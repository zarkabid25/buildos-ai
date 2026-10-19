"""Support desk (Phase 8, PLAT-046). One ticket table serves both requester
types (company and supplier) rather than two parallel tables, since the
staff-facing workflow (assignment, priority, status, messages) is identical
either way -- only exactly one of company_id/marketplace_supplier_id is ever
set, enforced in the service layer. Messages carry an `is_internal` flag:
an internal note is written by staff and must never be returned by any
company- or supplier-facing endpoint -- enforced in support_ticket_service.py,
not just by convention."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TimestampedBase
from app.models.enums import SupportAuthorType, SupportRequesterType, SupportTicketCategory, SupportTicketPriority, SupportTicketStatus


class SupportTicket(TimestampedBase):
    __tablename__ = "support_tickets"

    requester_type: Mapped[SupportRequesterType] = mapped_column(
        Enum(SupportRequesterType, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), index=True, nullable=False
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), index=True, nullable=True)
    marketplace_supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=True)
    opened_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    opened_by_supplier_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_users.id"), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[SupportTicketCategory] = mapped_column(
        Enum(SupportTicketCategory, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    priority: Mapped[SupportTicketPriority] = mapped_column(
        Enum(SupportTicketPriority, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=SupportTicketPriority.MEDIUM, nullable=False,
    )
    status: Mapped[SupportTicketStatus] = mapped_column(
        Enum(SupportTicketStatus, native_enum=False, length=30, values_callable=lambda e: [x.value for x in e]),
        default=SupportTicketStatus.OPEN, index=True, nullable=False,
    )
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["SupportTicketMessage"]] = relationship(order_by="SupportTicketMessage.created_at.asc()", cascade="all, delete-orphan")


class SupportTicketMessage(TimestampedBase):
    __tablename__ = "support_ticket_messages"

    ticket_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("support_tickets.id"), index=True, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    author_type: Mapped[SupportAuthorType] = mapped_column(
        Enum(SupportAuthorType, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author_supplier_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_users.id"), nullable=True)
    author_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
