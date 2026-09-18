"""material categories, materials, warehouses, inventory transactions

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

inventory_tx_type_enum = postgresql.ENUM(
    "stock_in", "stock_out", "transfer_in", "transfer_out", "allocation",
    name="inventory_transaction_type", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "material_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_material_categories_company_id", "material_categories", ["company_id"])

    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(50), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["material_categories.id"]),
    )
    op.create_index("ix_materials_company_id", "materials", ["company_id"])

    op.create_table(
        "warehouses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_warehouses_company_id", "warehouses", ["company_id"])

    inventory_tx_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("transaction_type", inventory_tx_type_enum, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transfer_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
    )
    op.create_index("ix_inventory_transactions_company_id", "inventory_transactions", ["company_id"])
    op.create_index("ix_inventory_transactions_material_id", "inventory_transactions", ["material_id"])
    op.create_index("ix_inventory_transactions_warehouse_id", "inventory_transactions", ["warehouse_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_warehouse_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_material_id", table_name="inventory_transactions")
    op.drop_index("ix_inventory_transactions_company_id", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    inventory_tx_type_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_warehouses_company_id", table_name="warehouses")
    op.drop_table("warehouses")

    op.drop_index("ix_materials_company_id", table_name="materials")
    op.drop_table("materials")

    op.drop_index("ix_material_categories_company_id", table_name="material_categories")
    op.drop_table("material_categories")
