"""platform staff roles, company onboarding status, platform audit log and
staff invitations (PLAT-006..010)

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # Plain strings (native_enum=False in the model), so adding a role/status
    # later never needs a migration -- same convention as RfqStatus.
    op.add_column(
        "platform_admins",
        sa.Column("role", sa.String(length=20), nullable=False, server_default="owner"),
    )
    # Legacy compatibility: every company that existed before this column was
    # added is backfilled to 'approved' (does not gate login either way).
    op.add_column(
        "companies",
        sa.Column("onboarding_status", sa.String(length=20), nullable=False, server_default="approved"),
    )

    op.create_table(
        "platform_audit_log",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", UUID, nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_platform_audit_log_action", "platform_audit_log", ["action"])

    op.create_table(
        "platform_invitations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["invited_by_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_platform_invitations_token_hash", "platform_invitations", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_platform_invitations_token_hash", table_name="platform_invitations")
    op.drop_table("platform_invitations")
    op.drop_index("ix_platform_audit_log_action", table_name="platform_audit_log")
    op.drop_table("platform_audit_log")
    op.drop_column("companies", "onboarding_status")
    op.drop_column("platform_admins", "role")
