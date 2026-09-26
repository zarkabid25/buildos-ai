import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TenantBase
from app.models.enums import AiProposalStatus, AiProposalType


class AiConversation(TenantBase):
    __tablename__ = "ai_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    messages: Mapped[list["AiMessage"]] = relationship(order_by="AiMessage.created_at")


class AiMessage(TenantBase):
    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_conversations.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_trace: Mapped[list | None] = mapped_column(JSON, nullable=True)


class AiProposal(TenantBase):
    """A change the assistant suggests. It is only a draft: nothing touches the
    real tables until a human approves it (CLAUDE.md rule 12)."""

    __tablename__ = "ai_proposals"

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_conversations.id"), nullable=True
    )
    proposal_type: Mapped[AiProposalType] = mapped_column(
        Enum(AiProposalType, name="ai_proposal_type", values_callable=lambda cls: [e.value for e in cls]),
        nullable=False,
    )
    status: Mapped[AiProposalStatus] = mapped_column(
        Enum(AiProposalStatus, name="ai_proposal_status", values_callable=lambda cls: [e.value for e in cls]),
        default=AiProposalStatus.PENDING,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
