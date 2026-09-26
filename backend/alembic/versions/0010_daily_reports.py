"""daily reports and photos

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("weather", sa.String(100), nullable=True),
        sa.Column("workers_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("work_completed", sa.Text(), nullable=True),
        sa.Column("materials_consumed", sa.Text(), nullable=True),
        sa.Column("equipment_used", sa.Text(), nullable=True),
        sa.Column("problems", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.UniqueConstraint("project_id", "report_date", name="uq_project_report_date"),
    )
    op.create_index("ix_daily_reports_company_id", "daily_reports", ["company_id"])
    op.create_index("ix_daily_reports_project_id", "daily_reports", ["project_id"])

    op.create_table(
        "daily_report_photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("daily_report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["daily_report_id"], ["daily_reports.id"]),
    )
    op.create_index("ix_daily_report_photos_company_id", "daily_report_photos", ["company_id"])
    op.create_index("ix_daily_report_photos_daily_report_id", "daily_report_photos", ["daily_report_id"])


def downgrade() -> None:
    op.drop_index("ix_daily_report_photos_daily_report_id", table_name="daily_report_photos")
    op.drop_index("ix_daily_report_photos_company_id", table_name="daily_report_photos")
    op.drop_table("daily_report_photos")
    op.drop_index("ix_daily_reports_project_id", table_name="daily_reports")
    op.drop_index("ix_daily_reports_company_id", table_name="daily_reports")
    op.drop_table("daily_reports")
