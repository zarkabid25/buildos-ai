"""Marketplace-to-ERP integration: company-supplier ERP linkage, RFQ
invitations, delivery reports (PLAT-021..027)

Revision ID: 0026
Revises: 0025
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # marketplace_company_supplier_links: link to the company's own ERP Supplier
    # row, preference/status flags, and allow a tenant user (not just platform
    # staff) to be the one who created the connection.
    op.add_column("marketplace_company_supplier_links", sa.Column("erp_supplier_id", UUID, nullable=True))
    op.add_column(
        "marketplace_company_supplier_links",
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "marketplace_company_supplier_links",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column("marketplace_company_supplier_links", sa.Column("linked_by_user_id", UUID, nullable=True))
    op.alter_column("marketplace_company_supplier_links", "linked_by_id", nullable=True)
    op.create_foreign_key(
        "fk_mcsl_erp_supplier", "marketplace_company_supplier_links", "suppliers", ["erp_supplier_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_mcsl_linked_by_user", "marketplace_company_supplier_links", "users", ["linked_by_user_id"], ["id"]
    )

    op.create_table(
        "marketplace_rfq_invitations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="invited"),
        sa.Column("invited_by_staff_id", UUID, nullable=True),
        sa.Column("invited_by_user_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["invited_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"]),
        sa.UniqueConstraint("rfq_id", "marketplace_supplier_id", name="uq_rfq_marketplace_supplier"),
    )
    op.create_index("ix_marketplace_rfq_invitations_company_id", "marketplace_rfq_invitations", ["company_id"])
    op.create_index("ix_marketplace_rfq_invitations_rfq_id", "marketplace_rfq_invitations", ["rfq_id"])
    op.create_index(
        "ix_marketplace_rfq_invitations_marketplace_supplier_id",
        "marketplace_rfq_invitations",
        ["marketplace_supplier_id"],
    )

    op.create_table(
        "marketplace_delivery_reports",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("purchase_order_id", UUID, nullable=False),
        sa.Column("external_reference", sa.String(100), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("reported_by_staff_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["reported_by_staff_id"], ["platform_admins.id"]),
        sa.UniqueConstraint("purchase_order_id", "external_reference", name="uq_delivery_report_reference"),
    )
    op.create_index("ix_marketplace_delivery_reports_company_id", "marketplace_delivery_reports", ["company_id"])
    op.create_index(
        "ix_marketplace_delivery_reports_purchase_order_id", "marketplace_delivery_reports", ["purchase_order_id"]
    )


def downgrade() -> None:
    op.drop_table("marketplace_delivery_reports")
    op.drop_table("marketplace_rfq_invitations")
    op.drop_constraint("fk_mcsl_linked_by_user", "marketplace_company_supplier_links", type_="foreignkey")
    op.drop_constraint("fk_mcsl_erp_supplier", "marketplace_company_supplier_links", type_="foreignkey")
    op.alter_column("marketplace_company_supplier_links", "linked_by_id", nullable=False)
    op.drop_column("marketplace_company_supplier_links", "linked_by_user_id")
    op.drop_column("marketplace_company_supplier_links", "status")
    op.drop_column("marketplace_company_supplier_links", "is_preferred")
    op.drop_column("marketplace_company_supplier_links", "erp_supplier_id")
