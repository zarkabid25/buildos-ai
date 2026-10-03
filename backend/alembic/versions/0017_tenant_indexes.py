"""company_id indexes missing from 0009 (attendance, employee assignments)

Found by comparing a fresh `alembic upgrade head` against the models: every
tenant table is filtered by company_id on every query, and these two were the
only ones without an index on it.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-06

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_attendance_company_id", "attendance", ["company_id"], if_not_exists=True)
    op.create_index(
        "ix_employee_project_assignments_company_id", "employee_project_assignments", ["company_id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_employee_project_assignments_company_id", table_name="employee_project_assignments")
    op.drop_index("ix_attendance_company_id", table_name="attendance")
