"""SaaS subscriptions, plans, invoices, manual payments, and legacy
entitlement grandfathering (PLAT-028..032)

Revision ID: 0028
Revises: 0027
Create Date: 2026-10-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_projects", sa.Integer(), nullable=True),
        sa.Column("max_team_members", sa.Integer(), nullable=True),
        sa.Column("ai_monthly_messages", sa.Integer(), nullable=True),
        sa.Column("storage_gb", sa.Integer(), nullable=True),
        sa.Column("marketplace_included", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("name", name="uq_subscription_plans_name"),
    )

    op.create_table(
        "plan_prices",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plan_id", UUID, nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("billing_period", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
    )
    op.create_index("ix_plan_prices_plan_id", "plan_prices", ["plan_id"])
    op.create_index(
        "uq_one_current_price_per_plan_currency_period",
        "plan_prices",
        ["plan_id", "currency", "billing_period"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
        sqlite_where=sa.text("is_current = 1"),
    )

    op.create_table(
        "company_subscriptions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("plan_id", UUID, nullable=False),
        sa.Column("plan_price_id", UUID, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="trialing"),
        sa.Column("billing_period", sa.String(10), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_period_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["plan_price_id"], ["plan_prices.id"]),
    )
    op.create_index("ix_company_subscriptions_company_id", "company_subscriptions", ["company_id"])
    op.create_index("ix_company_subscriptions_status", "company_subscriptions", ["status"])
    op.create_index(
        "uq_one_live_subscription_per_company",
        "company_subscriptions",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('trialing', 'active', 'pending_payment', 'grace_period')"),
        sqlite_where=sa.text("status IN ('trialing', 'active', 'pending_payment', 'grace_period')"),
    )

    op.create_table(
        "subscription_invoices",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("subscription_id", UUID, nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("billing_period_start", sa.Date(), nullable=False),
        sa.Column("billing_period_end", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["company_subscriptions.id"]),
        sa.UniqueConstraint("invoice_number", name="uq_subscription_invoices_invoice_number"),
    )
    op.create_index("ix_subscription_invoices_company_id", "subscription_invoices", ["company_id"])
    op.create_index("ix_subscription_invoices_subscription_id", "subscription_invoices", ["subscription_id"])
    op.create_index("ix_subscription_invoices_status", "subscription_invoices", ["status"])

    op.create_table(
        "invoice_line_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invoice_id", UUID, nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["subscription_invoices.id"]),
    )
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])

    op.create_table(
        "payment_submissions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("invoice_id", UUID, nullable=False),
        sa.Column("submitted_by_user_id", UUID, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("method", sa.String(30), nullable=False, server_default="bank_transfer"),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("proof_storage_key", sa.String(500), nullable=False),
        sa.Column("proof_content_type", sa.String(100), nullable=False),
        sa.Column("proof_filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("verified_by_staff_id", UUID, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["subscription_invoices.id"]),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["verified_by_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_payment_submissions_company_id", "payment_submissions", ["company_id"])
    op.create_index("ix_payment_submissions_invoice_id", "payment_submissions", ["invoice_id"])
    op.create_index("ix_payment_submissions_status", "payment_submissions", ["status"])

    op.create_table(
        "subscription_events",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("subscription_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(20), nullable=True),
        sa.Column("to_status", sa.String(20), nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("actor_staff_id", UUID, nullable=True),
        sa.Column("actor_user_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["company_subscriptions.id"]),
        sa.ForeignKeyConstraint(["actor_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index("ix_subscription_events_company_id", "subscription_events", ["company_id"])
    op.create_index("ix_subscription_events_subscription_id", "subscription_events", ["subscription_id"])

    op.create_table(
        "company_legacy_entitlements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", UUID, nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("granted_by_staff_id", UUID, nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_staff_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["granted_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["revoked_by_staff_id"], ["platform_admins.id"]),
        sa.UniqueConstraint("company_id", name="uq_company_legacy_entitlements_company_id"),
    )
    # No separate index here: the UniqueConstraint above already provides one.

    # PLAT-032: grandfather every company that existed before this migration.
    # Non-destructive -- an INSERT only, no existing row anywhere is touched.
    conn = op.get_bind()
    companies = conn.execute(sa.text("SELECT id FROM companies")).fetchall()
    legacy_table = sa.table(
        "company_legacy_entitlements",
        sa.column("id", UUID),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("company_id", UUID),
        sa.column("reason", sa.String),
    )
    if companies:
        import uuid as _uuid
        from datetime import datetime as _dt, timezone as _tz

        ts = _dt.now(_tz.utc)
        conn.execute(
            legacy_table.insert(),
            [
                {
                    "id": _uuid.uuid4(),
                    "created_at": ts,
                    "updated_at": ts,
                    "company_id": row[0],
                    "reason": "Grandfathered: existing company prior to Phase 5 (subscriptions/billing)",
                }
                for row in companies
            ],
        )


def downgrade() -> None:
    op.drop_table("company_legacy_entitlements")
    op.drop_table("subscription_events")
    op.drop_table("payment_submissions")
    op.drop_table("invoice_line_items")
    op.drop_table("subscription_invoices")
    op.drop_table("company_subscriptions")
    op.drop_table("plan_prices")
    op.drop_table("subscription_plans")
