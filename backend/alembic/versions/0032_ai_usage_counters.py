"""AI usage quota enforcement (Phase 9.1, Task 4): a durable per-company
monthly counter for ai_monthly_messages, previously just a displayed figure.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032"
down_revision: Union[str, None] = "0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "ai_usage_counters",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("message_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_ai_usage_counters_company_id", "ai_usage_counters", ["company_id"])
    op.create_index("ix_ai_usage_counters_company_period", "ai_usage_counters", ["company_id", "period"])
    op.create_unique_constraint("uq_ai_usage_counters_company_period", "ai_usage_counters", ["company_id", "period"])


def downgrade() -> None:
    op.drop_table("ai_usage_counters")
