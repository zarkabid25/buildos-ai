from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TimestampedBase


class PlatformAdmin(TimestampedBase):
    """BuildOS's own staff account, not a tenant. Deliberately has no company_id:
    this is the one place in the app that is allowed to see across companies,
    and only through the separate /platform/* routes and platform_access tokens."""

    __tablename__ = "platform_admins"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
