"""employees, attendance, equipment

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

attendance_status_enum = postgresql.ENUM(
    "present", "absent", "half_day", "leave", name="attendance_status", create_type=False,
)
equipment_status_enum = postgresql.ENUM(
    "available", "in_use", "maintenance", "retired", name="equipment_status", create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("designation", sa.String(100), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("daily_wage", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
    )
    op.create_index("ix_employees_company_id", "employees", ["company_id"])

    op.create_table(
        "employee_project_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("employee_id", "project_id", name="uq_employee_project"),
    )
    op.create_index(
        "ix_employee_project_assignments_employee_id", "employee_project_assignments", ["employee_id"]
    )
    op.create_index(
        "ix_employee_project_assignments_project_id", "employee_project_assignments", ["project_id"]
    )

    attendance_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", attendance_status_enum, nullable=False, server_default="present"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("employee_id", "attendance_date", name="uq_employee_attendance_date"),
    )
    op.create_index("ix_attendance_employee_id", "attendance", ["employee_id"])
    op.create_index("ix_attendance_project_id", "attendance", ["project_id"])

    equipment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "equipment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("equipment_type", sa.String(100), nullable=True),
        sa.Column("status", equipment_status_enum, nullable=False, server_default="available"),
        sa.Column("current_project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["current_project_id"], ["projects.id"]),
    )
    op.create_index("ix_equipment_company_id", "equipment", ["company_id"])

    op.create_table(
        "equipment_maintenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("equipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("maintenance_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cost", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("next_due_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["equipment_id"], ["equipment.id"]),
    )
    op.create_index("ix_equipment_maintenance_company_id", "equipment_maintenance", ["company_id"])
    op.create_index("ix_equipment_maintenance_equipment_id", "equipment_maintenance", ["equipment_id"])


def downgrade() -> None:
    op.drop_index("ix_equipment_maintenance_equipment_id", table_name="equipment_maintenance")
    op.drop_index("ix_equipment_maintenance_company_id", table_name="equipment_maintenance")
    op.drop_table("equipment_maintenance")

    op.drop_index("ix_equipment_company_id", table_name="equipment")
    op.drop_table("equipment")
    equipment_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_attendance_project_id", table_name="attendance")
    op.drop_index("ix_attendance_employee_id", table_name="attendance")
    op.drop_table("attendance")
    attendance_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_employee_project_assignments_project_id", table_name="employee_project_assignments")
    op.drop_index("ix_employee_project_assignments_employee_id", table_name="employee_project_assignments")
    op.drop_table("employee_project_assignments")

    op.drop_index("ix_employees_company_id", table_name="employees")
    op.drop_table("employees")
