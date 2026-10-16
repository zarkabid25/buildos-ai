"""Marketplace feature flag + quotation attribution (Phase 4.1 Tasks 3, 4)

Revision ID: 0027
Revises: 0026
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Disabled by default for every company, including every one that existed
    # before this column was added.
    op.add_column(
        "companies",
        sa.Column("marketplace_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "marketplace_quotation_attributions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("quotation_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("submitted_by_staff_id", UUID, nullable=False),
        sa.Column("method", sa.String(50), nullable=False, server_default="platform_staff_assisted"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["submitted_by_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_marketplace_quotation_attributions_company_id", "marketplace_quotation_attributions", ["company_id"])
    op.create_index("ix_marketplace_quotation_attributions_rfq_id", "marketplace_quotation_attributions", ["rfq_id"])
    op.create_index("ix_marketplace_quotation_attributions_quotation_id", "marketplace_quotation_attributions", ["quotation_id"])
    op.create_index(
        "ix_marketplace_quotation_attributions_marketplace_supplier_id",
        "marketplace_quotation_attributions",
        ["marketplace_supplier_id"],
    )


def downgrade() -> None:
    op.drop_table("marketplace_quotation_attributions")
    op.drop_column("companies", "marketplace_enabled")
