"""CRM organizations, contacts, activities (PLAT-011..015)

Revision ID: 0024
Revises: 0023
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "crm_organizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pipeline_type", sa.String(30), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False, server_default="new"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("website", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("owner_staff_id", UUID, nullable=True),
        sa.Column("converted_company_id", UUID, nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["owner_staff_id"], ["platform_admins.id"]),
        sa.ForeignKeyConstraint(["converted_company_id"], ["companies.id"]),
    )
    op.create_index("ix_crm_organizations_pipeline_type", "crm_organizations", ["pipeline_type"])
    op.create_index("ix_crm_organizations_stage", "crm_organizations", ["stage"])

    op.create_table(
        "crm_contacts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(100), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"]),
    )
    op.create_index("ix_crm_contacts_organization_id", "crm_contacts", ["organization_id"])

    op.create_table(
        "crm_activities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(500), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", UUID, nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["crm_organizations.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["platform_admins.id"]),
    )
    op.create_index("ix_crm_activities_organization_id", "crm_activities", ["organization_id"])
    op.create_index("ix_crm_activities_due_at", "crm_activities", ["due_at"])


def downgrade() -> None:
    op.drop_index("ix_crm_activities_due_at", table_name="crm_activities")
    op.drop_index("ix_crm_activities_organization_id", table_name="crm_activities")
    op.drop_table("crm_activities")
    op.drop_index("ix_crm_contacts_organization_id", table_name="crm_contacts")
    op.drop_table("crm_contacts")
    op.drop_index("ix_crm_organizations_stage", table_name="crm_organizations")
    op.drop_index("ix_crm_organizations_pipeline_type", table_name="crm_organizations")
    op.drop_table("crm_organizations")
