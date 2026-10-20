"""Transactional email adapter (Phase 9.1, Task 3): adds template_key and a
unique dedup_key to email_delivery_logs so a retried request never sends
the same notification twice.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: Union[str, None] = "0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_delivery_logs", sa.Column("template_key", sa.String(50), nullable=True))
    op.add_column("email_delivery_logs", sa.Column("dedup_key", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_email_delivery_logs_dedup_key", "email_delivery_logs", ["dedup_key"])


def downgrade() -> None:
    op.drop_constraint("uq_email_delivery_logs_dedup_key", "email_delivery_logs", type_="unique")
    op.drop_column("email_delivery_logs", "dedup_key")
    op.drop_column("email_delivery_logs", "template_key")
