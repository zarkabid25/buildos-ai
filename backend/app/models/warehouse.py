from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase


class Warehouse(TenantBase):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
