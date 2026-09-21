"""material requests, purchase orders, goods receipts

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

material_request_status_enum = postgresql.ENUM(
    "pending", "approved", "rejected", "converted",
    name="material_request_status", create_type=False,
)
purchase_order_status_enum = postgresql.ENUM(
    "draft", "pending_approval", "approved", "partially_received", "received", "cancelled",
    name="purchase_order_status", create_type=False,
)


def upgrade() -> None:
    material_request_status_enum.create(op.get_bind(), checkfirst=True)
    purchase_order_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "material_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", material_request_status_enum, nullable=False, server_default="pending"),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"]),
    )
    op.create_index("ix_material_requests_company_id", "material_requests", ["company_id"])
    op.create_index("ix_material_requests_project_id", "material_requests", ["project_id"])

    op.create_table(
        "material_request_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["material_request_id"], ["material_requests.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
    )
    op.create_index("ix_material_request_items_company_id", "material_request_items", ["company_id"])
    op.create_index(
        "ix_material_request_items_material_request_id", "material_request_items", ["material_request_id"]
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("material_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", purchase_order_status_enum, nullable=False, server_default="draft"),
        sa.Column("po_number", sa.String(50), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["material_request_id"], ["material_requests.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["users.id"]),
    )
    op.create_index("ix_purchase_orders_company_id", "purchase_orders", ["company_id"])

    op.create_table(
        "purchase_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 2), nullable=False),
        sa.Column("quantity_received", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
    )
    op.create_index("ix_purchase_order_items_company_id", "purchase_order_items", ["company_id"])
    op.create_index(
        "ix_purchase_order_items_purchase_order_id", "purchase_order_items", ["purchase_order_id"]
    )

    op.create_table(
        "goods_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("received_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
    )
    op.create_index("ix_goods_receipts_company_id", "goods_receipts", ["company_id"])
    op.create_index("ix_goods_receipts_purchase_order_id", "goods_receipts", ["purchase_order_id"])

    op.create_table(
        "goods_receipt_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("goods_receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_received", sa.Numeric(18, 3), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["goods_receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(["purchase_order_item_id"], ["purchase_order_items.id"]),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
    )
    op.create_index("ix_goods_receipt_items_company_id", "goods_receipt_items", ["company_id"])
    op.create_index(
        "ix_goods_receipt_items_goods_receipt_id", "goods_receipt_items", ["goods_receipt_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_goods_receipt_items_goods_receipt_id", table_name="goods_receipt_items")
    op.drop_index("ix_goods_receipt_items_company_id", table_name="goods_receipt_items")
    op.drop_table("goods_receipt_items")

    op.drop_index("ix_goods_receipts_purchase_order_id", table_name="goods_receipts")
    op.drop_index("ix_goods_receipts_company_id", table_name="goods_receipts")
    op.drop_table("goods_receipts")

    op.drop_index("ix_purchase_order_items_purchase_order_id", table_name="purchase_order_items")
    op.drop_index("ix_purchase_order_items_company_id", table_name="purchase_order_items")
    op.drop_table("purchase_order_items")

    op.drop_index("ix_purchase_orders_company_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")

    op.drop_index("ix_material_request_items_material_request_id", table_name="material_request_items")
    op.drop_index("ix_material_request_items_company_id", table_name="material_request_items")
    op.drop_table("material_request_items")

    op.drop_index("ix_material_requests_project_id", table_name="material_requests")
    op.drop_index("ix_material_requests_company_id", table_name="material_requests")
    op.drop_table("material_requests")

    purchase_order_status_enum.drop(op.get_bind(), checkfirst=True)
    material_request_status_enum.drop(op.get_bind(), checkfirst=True)
