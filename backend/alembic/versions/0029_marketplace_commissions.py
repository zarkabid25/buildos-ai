"""Marketplace commissions: supplier agreements, PO attribution, the
commission ledger, disputes, and commission invoices/payments (PLAT-033..037)

Revision ID: 0029
Revises: 0028
Create Date: 2026-10-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "supplier_commission_agreements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("basis", sa.String(20), nullable=False),
        sa.Column("rate", sa.Numeric(7, 4), nullable=True),
        sa.Column("fixed_fee_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("earning_trigger", sa.String(20), nullable=False, server_default="on_payment"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_staff_id", UUID, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_supplier_commission_agreements_marketplace_supplier_id", "supplier_commission_agreements", ["marketplace_supplier_id"])
    op.create_index("ix_supplier_commission_agreements_status", "supplier_commission_agreements", ["status"])
    op.create_index(
        "uq_one_active_agreement_per_supplier",
        "supplier_commission_agreements",
        ["marketplace_supplier_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "marketplace_po_attributions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("purchase_order_id", UUID, nullable=False),
        sa.Column("rfq_id", UUID, nullable=False),
        sa.Column("quotation_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("attributed_amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["rfq_id"], ["rfqs.id"]),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.UniqueConstraint("purchase_order_id", name="uq_marketplace_po_attributions_purchase_order_id"),
    )
    op.create_index("ix_marketplace_po_attributions_company_id", "marketplace_po_attributions", ["company_id"])
    op.create_index("ix_marketplace_po_attributions_marketplace_supplier_id", "marketplace_po_attributions", ["marketplace_supplier_id"])

    op.create_table(
        "commission_ledger_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("purchase_order_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("supplier_payment_id", UUID, nullable=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("agreement_id", UUID, nullable=True),
        sa.Column("basis_snapshot", sa.String(20), nullable=True),
        sa.Column("rate_snapshot", sa.Numeric(7, 4), nullable=True),
        sa.Column("fixed_fee_snapshot", sa.Numeric(18, 2), nullable=True),
        sa.Column("base_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("related_entry_id", UUID, nullable=True),
        sa.Column("invoiced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("created_by_staff_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["supplier_payment_id"], ["supplier_payments.id"]),
        sa.ForeignKeyConstraint(["agreement_id"], ["supplier_commission_agreements.id"]),
        sa.ForeignKeyConstraint(["related_entry_id"], ["commission_ledger_entries.id"]),
        sa.ForeignKeyConstraint(["created_by_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_commission_ledger_entries_company_id", "commission_ledger_entries", ["company_id"])
    op.create_index("ix_commission_ledger_entries_purchase_order_id", "commission_ledger_entries", ["purchase_order_id"])
    op.create_index("ix_commission_ledger_entries_marketplace_supplier_id", "commission_ledger_entries", ["marketplace_supplier_id"])
    op.create_index("ix_commission_ledger_entries_kind", "commission_ledger_entries", ["kind"])
    op.create_index(
        "uq_one_accrual_per_supplier_payment",
        "commission_ledger_entries",
        ["supplier_payment_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'accrual'"),
        sqlite_where=sa.text("kind = 'accrual'"),
    )

    op.create_table(
        "commission_disputes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ledger_entry_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("raised_by_staff_id", UUID, nullable=False),
        sa.Column("reviewed_by_staff_id", UUID, nullable=True),
        sa.Column("resolution_notes", sa.String(1000), nullable=True),
        sa.Column("resulting_entry_id", UUID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["commission_ledger_entries.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["raised_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["resulting_entry_id"], ["commission_ledger_entries.id"]),
    )
    op.create_index("ix_commission_disputes_ledger_entry_id", "commission_disputes", ["ledger_entry_id"])
    op.create_index("ix_commission_disputes_marketplace_supplier_id", "commission_disputes", ["marketplace_supplier_id"])
    op.create_index("ix_commission_disputes_status", "commission_disputes", ["status"])

    op.create_table(
        "commission_invoices",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("created_by_staff_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["created_by_staff_id"], ["platform_admins.id"]),
        sa.UniqueConstraint("invoice_number", name="uq_commission_invoices_invoice_number"),
    )
    op.create_index("ix_commission_invoices_marketplace_supplier_id", "commission_invoices", ["marketplace_supplier_id"])
    op.create_index("ix_commission_invoices_status", "commission_invoices", ["status"])

    op.create_table(
        "commission_invoice_line_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_id", UUID, nullable=False),
        sa.Column("ledger_entry_id", UUID, nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["commission_invoices.id"]),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["commission_ledger_entries.id"]),
        sa.UniqueConstraint("ledger_entry_id", name="uq_commission_invoice_line_items_ledger_entry_id"),
    )
    op.create_index("ix_commission_invoice_line_items_invoice_id", "commission_invoice_line_items", ["invoice_id"])

    op.create_table(
        "commission_payments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_id", UUID, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("method", sa.String(30), nullable=False, server_default="bank_transfer"),
        sa.Column("receipt_reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("recorded_by_staff_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["commission_invoices.id"]),
        sa.ForeignKeyConstraint(["recorded_by_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_commission_payments_invoice_id", "commission_payments", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("commission_payments")
    op.drop_table("commission_invoice_line_items")
    op.drop_table("commission_invoices")
    op.drop_table("commission_disputes")
    op.drop_table("commission_ledger_entries")
    op.drop_table("marketplace_po_attributions")
    op.drop_table("supplier_commission_agreements")
