"""link BOQ items to materials (BOQ vs Actual)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("boq_items", sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_boq_items_material_id", "boq_items", "materials", ["material_id"], ["id"])
    op.create_index("ix_boq_items_material_id", "boq_items", ["material_id"])


def downgrade() -> None:
    op.drop_index("ix_boq_items_material_id", table_name="boq_items")
    op.drop_constraint("fk_boq_items_material_id", "boq_items", type_="foreignkey")
    op.drop_column("boq_items", "material_id")
