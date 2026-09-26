import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TenantBase


class DailyReport(TenantBase):
    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint("project_id", "report_date", name="uq_project_report_date"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    weather: Mapped[str | None] = mapped_column(String(100), nullable=True)
    workers_count: Mapped[int] = mapped_column(Integer, default=0)
    work_completed: Mapped[str | None] = mapped_column(Text, nullable=True)
    materials_consumed: Mapped[str | None] = mapped_column(Text, nullable=True)
    equipment_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    problems: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    photos: Mapped[list["DailyReportPhoto"]] = relationship()


class DailyReportPhoto(TenantBase):
    __tablename__ = "daily_report_photos"

    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_reports.id"), index=True, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
