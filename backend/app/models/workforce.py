import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase
from app.models.enums import AttendanceStatus


class Employee(TenantBase):
    __tablename__ = "employees"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    daily_wage: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)


class EmployeeProjectAssignment(TenantBase):
    __tablename__ = "employee_project_assignments"
    __table_args__ = (UniqueConstraint("employee_id", "project_id", name="uq_employee_project"),)

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )


class Attendance(TenantBase):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_employee_attendance_date"),)

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id"), index=True, nullable=False
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(
            AttendanceStatus,
            name="attendance_status",
            values_callable=lambda cls: [e.value for e in cls],
        ),
        default=AttendanceStatus.PRESENT,
        nullable=False,
    )
