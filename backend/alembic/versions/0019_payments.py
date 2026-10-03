"""supplier payments and client receipts (BUILD-054)

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _payment_columns() -> list[sa.Column]:
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_by_id", UUID, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "supplier_payments",
        *_payment_columns(),
        sa.Column("purchase_order_id", UUID, nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )
    op.create_index("ix_supplier_payments_company_id", "supplier_payments", ["company_id"])
    op.create_index("ix_supplier_payments_purchase_order_id", "supplier_payments", ["purchase_order_id"])

    op.create_table(
        "client_receipts",
        *_payment_columns(),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )
    op.create_index("ix_client_receipts_company_id", "client_receipts", ["company_id"])
    op.create_index("ix_client_receipts_project_id", "client_receipts", ["project_id"])


def downgrade() -> None:
    op.drop_table("client_receipts")
    op.drop_table("supplier_payments")
