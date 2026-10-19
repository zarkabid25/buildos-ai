"""Public website lead capture, supplier applications, support desk, and
platform/supplier notifications (PLAT-043..047)

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031"
down_revision: Union[str, None] = "0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Postgres 12+ allows ALTER TYPE ... ADD VALUE inside a transaction (the
    # new value just can't be used in that same transaction) -- additive,
    # every existing row/value untouched.
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'support_ticket_reply'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'support_ticket_resolved'")

    op.create_table(
        "demo_requests",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("crm_organization_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["crm_organization_id"], ["crm_organizations.id"]),
    )
    op.create_index("ix_demo_requests_email", "demo_requests", ["email"])

    op.create_table(
        "supplier_applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("business_registration_info", sa.String(500), nullable=True),
        sa.Column("categories", sa.String(500), nullable=True),
        sa.Column("delivery_locations", sa.String(500), nullable=True),
        sa.Column("business_description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.String(1000), nullable=True),
        sa.Column("reviewed_by_staff_id", UUID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("marketplace_supplier_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["reviewed_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
    )
    op.create_index("ix_supplier_applications_email", "supplier_applications", ["email"])
    op.create_index("ix_supplier_applications_status", "supplier_applications", ["status"])

    op.create_table(
        "supplier_application_documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("application_id", UUID, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["supplier_applications.id"]),
    )
    op.create_index("ix_supplier_application_documents_application_id", "supplier_application_documents", ["application_id"])

    op.create_table(
        "support_tickets",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requester_type", sa.String(20), nullable=False),
        sa.Column("company_id", UUID, nullable=True),
        sa.Column("marketplace_supplier_id", UUID, nullable=True),
        sa.Column("opened_by_user_id", UUID, nullable=True),
        sa.Column("opened_by_supplier_user_id", UUID, nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("assigned_staff_id", UUID, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["opened_by_supplier_user_id"], ["supplier_users.id"]),
        sa.ForeignKeyConstraint(["assigned_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_support_tickets_requester_type", "support_tickets", ["requester_type"])
    op.create_index("ix_support_tickets_company_id", "support_tickets", ["company_id"])
    op.create_index("ix_support_tickets_marketplace_supplier_id", "support_tickets", ["marketplace_supplier_id"])
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"])

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticket_id", UUID, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("author_type", sa.String(20), nullable=False),
        sa.Column("author_user_id", UUID, nullable=True),
        sa.Column("author_supplier_user_id", UUID, nullable=True),
        sa.Column("author_staff_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["author_supplier_user_id"], ["supplier_users.id"]),
        sa.ForeignKeyConstraint(["author_staff_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"])
    op.create_index("ix_support_ticket_messages_is_internal", "support_ticket_messages", ["is_internal"])

    op.create_table(
        "supplier_notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_user_id", UUID, nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(500), nullable=True),
        sa.Column("link", sa.String(255), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["supplier_user_id"], ["supplier_users.id"]),
    )
    op.create_index("ix_supplier_notifications_supplier_user_id", "supplier_notifications", ["supplier_user_id"])

    op.create_table(
        "platform_notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.String(500), nullable=True),
        sa.Column("link", sa.String(255), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "email_delivery_logs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.String(500), nullable=True),
    )
    op.create_index("ix_email_delivery_logs_status", "email_delivery_logs", ["status"])


def downgrade() -> None:
    op.drop_table("email_delivery_logs")
    op.drop_table("platform_notifications")
    op.drop_table("supplier_notifications")
    op.drop_table("support_ticket_messages")
    op.drop_table("support_tickets")
    op.drop_table("supplier_application_documents")
    op.drop_table("supplier_applications")
    op.drop_table("demo_requests")
    # Postgres has no DROP VALUE for enums; the two added notification_type
    # values are left in place on downgrade (harmless, matches this
    # project's existing precedent of not reversing additive enum changes).
