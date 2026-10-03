"""RFQs, invited suppliers, quotations (BUILD-041..043)

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def _base() -> list[sa.Column]:
    return [
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "rfqs",
        *_base(),
        sa.Column("rfq_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("project_id", UUID, nullable=True),
        sa.Column("material_request_id", UUID, nullable=True),
        sa.Column("response_due", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.Column("awarded_quotation_id", UUID, nullable=True),
        sa.Column("purchase_order_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["material_request_id"], ["material_requests.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
    )
    op.create_index("ix_rfqs_company_id", "rfqs", ["company_id"])
    op.create_index("ix_rfqs_project_id", "rfqs", ["project_id"])

    op.create_table(
        "rfq_items",
        *_base(),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("material_id", UUID, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
    )
    op.create_index("ix_rfq_items_company_id", "rfq_items", ["company_id"])
    op.create_index("ix_rfq_items_rfq_id", "rfq_items", ["rfq_id"])

    op.create_table(
        "rfq_suppliers",
        *_base(),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.UniqueConstraint("rfq_id", "supplier_id", name="uq_rfq_supplier"),
    )
    op.create_index("ix_rfq_suppliers_company_id", "rfq_suppliers", ["company_id"])
    op.create_index("ix_rfq_suppliers_rfq_id", "rfq_suppliers", ["rfq_id"])

    op.create_table(
        "quotations",
        *_base(),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.UniqueConstraint("rfq_id", "supplier_id", name="uq_quotation_supplier"),
    )
    op.create_index("ix_quotations_company_id", "quotations", ["company_id"])
    op.create_index("ix_quotations_rfq_id", "quotations", ["rfq_id"])

    op.create_table(
        "quotation_items",
        *_base(),
        sa.Column("quotation_id", UUID, nullable=False),
        sa.Column("rfq_item_id", UUID, nullable=False),
        sa.Column("rate", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["rfq_item_id"], ["rfq_items.id"]),
    )
    op.create_index("ix_quotation_items_company_id", "quotation_items", ["company_id"])
    op.create_index("ix_quotation_items_quotation_id", "quotation_items", ["quotation_id"])


def downgrade() -> None:
    for table in ("quotation_items", "quotations", "rfq_suppliers", "rfq_items", "rfqs"):
        op.drop_table(table)
