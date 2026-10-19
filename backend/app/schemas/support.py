import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SupportAuthorType, SupportRequesterType, SupportTicketCategory, SupportTicketPriority, SupportTicketStatus


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=255)
    category: SupportTicketCategory
    priority: SupportTicketPriority = SupportTicketPriority.MEDIUM
    message: str = Field(min_length=1, max_length=5000)


class SupportTicketMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class SupportTicketMessageRead(BaseModel):
    id: uuid.UUID
    body: str
    is_internal: bool
    author_type: SupportAuthorType
    author_name: str | None = None
    created_at: datetime


class SupportTicketUpdate(BaseModel):
    """Staff-only: assignment, priority, status."""

    assigned_staff_id: uuid.UUID | None = None
    priority: SupportTicketPriority | None = None
    status: SupportTicketStatus | None = None


class SupportTicketRead(BaseModel):
    id: uuid.UUID
    requester_type: SupportRequesterType
    company_id: uuid.UUID | None
    company_name: str | None = None
    marketplace_supplier_id: uuid.UUID | None
    marketplace_supplier_name: str | None = None
    subject: str
    category: SupportTicketCategory
    priority: SupportTicketPriority
    status: SupportTicketStatus
    assigned_staff_id: uuid.UUID | None
    assigned_staff_name: str | None = None
    resolved_at: datetime | None
    messages: list[SupportTicketMessageRead]
    created_at: datetime


class SupportTicketSummary(BaseModel):
    id: uuid.UUID
    requester_type: SupportRequesterType
    company_name: str | None = None
    marketplace_supplier_name: str | None = None
    subject: str
    category: SupportTicketCategory
    priority: SupportTicketPriority
    status: SupportTicketStatus
    created_at: datetime
