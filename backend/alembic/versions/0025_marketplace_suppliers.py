"""Marketplace supplier registry, verification, catalog, and future-integration
links (PLAT-016..020)

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "marketplace_suppliers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("onboarded_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["onboarded_by_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_marketplace_suppliers_name", "marketplace_suppliers", ["name"])
    op.create_index("ix_marketplace_suppliers_verification_status", "marketplace_suppliers", ["verification_status"])

    op.create_table(
        "marketplace_supplier_contacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["supplier_id"], ["marketplace_suppliers.id"]),
    )
    op.create_index("ix_marketplace_supplier_contacts_supplier_id", "marketplace_supplier_contacts", ["supplier_id"])

    op.create_table(
        "marketplace_supplier_documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("uploaded_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_marketplace_supplier_documents_supplier_id", "marketplace_supplier_documents", ["supplier_id"])

    op.create_table(
        "marketplace_supplier_categories",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["marketplace_suppliers.id"]),
        sa.UniqueConstraint("supplier_id", "category", name="uq_marketplace_supplier_category"),
    )
    op.create_index("ix_marketplace_supplier_categories_supplier_id", "marketplace_supplier_categories", ["supplier_id"])

    op.create_table(
        "marketplace_supplier_coverage_areas",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("area", sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(["supplier_id"], ["marketplace_suppliers.id"]),
        sa.UniqueConstraint("supplier_id", "area", name="uq_marketplace_supplier_coverage_area"),
    )
    op.create_index(
        "ix_marketplace_supplier_coverage_areas_supplier_id", "marketplace_supplier_coverage_areas", ["supplier_id"]
    )

    op.create_table(
        "marketplace_products",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("minimum_order_quantity", sa.Numeric(18, 3), nullable=False, server_default="1"),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["supplier_id"], ["marketplace_suppliers.id"]),
    )
    op.create_index("ix_marketplace_products_supplier_id", "marketplace_products", ["supplier_id"])

    op.create_table(
        "marketplace_company_supplier_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("linked_by_id", UUID, nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["linked_by_id"], ["platform_admins.id"]),
        sa.UniqueConstraint("company_id", "marketplace_supplier_id", name="uq_company_marketplace_supplier"),
    )
    op.create_index("ix_marketplace_company_supplier_links_company_id", "marketplace_company_supplier_links", ["company_id"])
    op.create_index(
        "ix_marketplace_company_supplier_links_marketplace_supplier_id",
        "marketplace_company_supplier_links",
        ["marketplace_supplier_id"],
    )

    op.create_table(
        "marketplace_material_mappings",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("material_id", UUID, nullable=False),
        sa.Column("marketplace_product_id", UUID, nullable=False),
        sa.Column("mapped_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.ForeignKeyConstraint(["marketplace_product_id"], ["marketplace_products.id"]),
        sa.ForeignKeyConstraint(["mapped_by_id"], ["platform_admins.id"]),
        sa.UniqueConstraint("company_id", "material_id", "marketplace_product_id", name="uq_material_mapping"),
    )
    op.create_index("ix_marketplace_material_mappings_company_id", "marketplace_material_mappings", ["company_id"])
    op.create_index("ix_marketplace_material_mappings_material_id", "marketplace_material_mappings", ["material_id"])
    op.create_index(
        "ix_marketplace_material_mappings_marketplace_product_id",
        "marketplace_material_mappings",
        ["marketplace_product_id"],
    )


def downgrade() -> None:
    op.drop_table("marketplace_material_mappings")
    op.drop_table("marketplace_company_supplier_links")
    op.drop_table("marketplace_products")
    op.drop_table("marketplace_supplier_coverage_areas")
    op.drop_table("marketplace_supplier_categories")
    op.drop_table("marketplace_supplier_documents")
    op.drop_table("marketplace_supplier_contacts")
    op.drop_table("marketplace_suppliers")
