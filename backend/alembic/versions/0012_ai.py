"""ai conversations, messages, proposals

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

proposal_type_enum = postgresql.ENUM("material_request", name="ai_proposal_type", create_type=False)
proposal_status_enum = postgresql.ENUM(
    "pending", "approved", "rejected", name="ai_proposal_status", create_type=False
)


def upgrade() -> None:
    proposal_type_enum.create(op.get_bind(), checkfirst=True)
    proposal_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_ai_conversations_company_id", "ai_conversations", ["company_id"])
    op.create_index("ix_ai_conversations_user_id", "ai_conversations", ["user_id"])

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_trace", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
    )
    op.create_index("ix_ai_messages_company_id", "ai_messages", ["company_id"])
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])

    op.create_table(
        "ai_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposal_type", proposal_type_enum, nullable=False),
        sa.Column("status", proposal_status_enum, nullable=False, server_default="pending"),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_ref", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"]),
    )
    op.create_index("ix_ai_proposals_company_id", "ai_proposals", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_proposals_company_id", table_name="ai_proposals")
    op.drop_table("ai_proposals")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_index("ix_ai_messages_company_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_user_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_company_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
    proposal_status_enum.drop(op.get_bind(), checkfirst=True)
    proposal_type_enum.drop(op.get_bind(), checkfirst=True)
