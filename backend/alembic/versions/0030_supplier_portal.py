"""Supplier self-service portal: supplier users, memberships, invitations;
widens quotation-attribution and delivery-report ownership to allow a
supplier's own portal user as the actor, alongside the existing
platform-staff path (PLAT-038..042)

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: Union[str, None] = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "supplier_users",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("email", name="uq_supplier_users_email"),
    )
    # No separate index: the UniqueConstraint above already provides one (same
    # convention as company_legacy_entitlements in migration 0028).

    op.create_table(
        "supplier_memberships",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supplier_user_id", UUID, nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["supplier_user_id"], ["supplier_users.id"]),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.UniqueConstraint("supplier_user_id", "marketplace_supplier_id", name="uq_supplier_membership"),
    )
    op.create_index("ix_supplier_memberships_supplier_user_id", "supplier_memberships", ["supplier_user_id"])
    op.create_index("ix_supplier_memberships_marketplace_supplier_id", "supplier_memberships", ["marketplace_supplier_id"])
    op.create_index("ix_supplier_memberships_status", "supplier_memberships", ["status"])

    op.create_table(
        "supplier_invitations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marketplace_supplier_id", UUID, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_by_staff_id", UUID, nullable=True),
        sa.Column("invited_by_supplier_user_id", UUID, nullable=True),
        sa.ForeignKeyConstraint(["marketplace_supplier_id"], ["marketplace_suppliers.id"]),
        sa.ForeignKeyConstraint(["invited_by_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["invited_by_supplier_user_id"], ["supplier_users.id"]),
        sa.UniqueConstraint("token_hash", name="uq_supplier_invitations_token_hash"),
    )
    op.create_index("ix_supplier_invitations_marketplace_supplier_id", "supplier_invitations", ["marketplace_supplier_id"])

    # Widen quotation attribution to allow a supplier's own portal user as the
    # actor, alongside the existing platform-staff path. Loosening an existing
    # NOT NULL column is additive/backward-compatible: every pre-existing row
    # already has submitted_by_staff_id populated.
    with op.batch_alter_table("marketplace_quotation_attributions") as batch_op:
        batch_op.alter_column("submitted_by_staff_id", existing_type=UUID, nullable=True)
        batch_op.add_column(sa.Column("submitted_by_supplier_user_id", UUID, nullable=True))
        batch_op.create_foreign_key(
            "fk_marketplace_quotation_attributions_supplier_user", "supplier_users", ["submitted_by_supplier_user_id"], ["id"]
        )

    # Same widening for delivery reports.
    with op.batch_alter_table("marketplace_delivery_reports") as batch_op:
        batch_op.alter_column("reported_by_staff_id", existing_type=UUID, nullable=True)
        batch_op.add_column(sa.Column("reported_by_supplier_user_id", UUID, nullable=True))
        batch_op.create_foreign_key(
            "fk_marketplace_delivery_reports_supplier_user", "supplier_users", ["reported_by_supplier_user_id"], ["id"]
        )

    # Same widening for verification documents -- a supplier can now upload
    # its own via the portal, alongside the existing staff-uploaded path.
    with op.batch_alter_table("marketplace_supplier_documents") as batch_op:
        batch_op.alter_column("uploaded_by_id", existing_type=UUID, nullable=True)
        batch_op.add_column(sa.Column("uploaded_by_supplier_user_id", UUID, nullable=True))
        batch_op.create_foreign_key(
            "fk_marketplace_supplier_documents_supplier_user", "supplier_users", ["uploaded_by_supplier_user_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("marketplace_supplier_documents") as batch_op:
        batch_op.drop_constraint("fk_marketplace_supplier_documents_supplier_user", type_="foreignkey")
        batch_op.drop_column("uploaded_by_supplier_user_id")
        batch_op.alter_column("uploaded_by_id", existing_type=UUID, nullable=False)

    with op.batch_alter_table("marketplace_delivery_reports") as batch_op:
        batch_op.drop_constraint("fk_marketplace_delivery_reports_supplier_user", type_="foreignkey")
        batch_op.drop_column("reported_by_supplier_user_id")
        batch_op.alter_column("reported_by_staff_id", existing_type=UUID, nullable=False)

    with op.batch_alter_table("marketplace_quotation_attributions") as batch_op:
        batch_op.drop_constraint("fk_marketplace_quotation_attributions_supplier_user", type_="foreignkey")
        batch_op.drop_column("submitted_by_supplier_user_id")
        batch_op.alter_column("submitted_by_staff_id", existing_type=UUID, nullable=False)

    op.drop_table("supplier_invitations")
    op.drop_table("supplier_memberships")
    op.drop_table("supplier_users")
