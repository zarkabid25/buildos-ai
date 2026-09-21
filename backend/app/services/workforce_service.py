import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import AttendanceStatus
from app.models.workforce import Attendance, Employee, EmployeeProjectAssignment
from app.schemas.workforce import (
    AttendanceCreate,
    EmployeeAssignmentCreate,
    EmployeeCreate,
    EmployeeProductivity,
    EmployeeUpdate,
    ProjectLaborCost,
)
from app.services.project_service import get_project

# ---- Employees ---------------------------------------------------------------


def list_employees(db: Session, company_id: uuid.UUID) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.company_id == company_id)
        .order_by(Employee.full_name.asc())
        .all()
    )


def get_employee(db: Session, company_id: uuid.UUID, employee_id: uuid.UUID) -> Employee:
    employee = (
        db.query(Employee)
        .filter(Employee.company_id == company_id, Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    return employee


def create_employee(db: Session, company_id: uuid.UUID, payload: EmployeeCreate) -> Employee:
    employee = Employee(company_id=company_id, **payload.model_dump())
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def update_employee(
    db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, payload: EmployeeUpdate
) -> Employee:
    employee = get_employee(db, company_id, employee_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


# ---- Project assignment -------------------------------------------------------


def assign_to_project(
    db: Session, company_id: uuid.UUID, employee_id: uuid.UUID, payload: EmployeeAssignmentCreate
) -> EmployeeProjectAssignment:
    get_employee(db, company_id, employee_id)
    get_project(db, company_id, payload.project_id)

    existing = (
        db.query(EmployeeProjectAssignment)
        .filter(
            EmployeeProjectAssignment.employee_id == employee_id,
            EmployeeProjectAssignment.project_id == payload.project_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Employee is already assigned to this project")

    assignment = EmployeeProjectAssignment(
        company_id=company_id, employee_id=employee_id, project_id=payload.project_id
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def list_project_assignments(
    db: Session, company_id: uuid.UUID, employee_id: uuid.UUID
) -> list[EmployeeProjectAssignment]:
    get_employee(db, company_id, employee_id)
    return (
        db.query(EmployeeProjectAssignment)
        .filter(
            EmployeeProjectAssignment.company_id == company_id,
            EmployeeProjectAssignment.employee_id == employee_id,
        )
        .all()
    )


# ---- Attendance + labor cost (BUILD-065, 066, 067) ----------------------------


def record_attendance(db: Session, company_id: uuid.UUID, payload: AttendanceCreate) -> Attendance:
    get_employee(db, company_id, payload.employee_id)
    get_project(db, company_id, payload.project_id)

    existing = (
        db.query(Attendance)
        .filter(
            Attendance.employee_id == payload.employee_id,
            Attendance.attendance_date == payload.attendance_date,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Attendance already recorded for this employee on this date"
        )

    record = Attendance(company_id=company_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_attendance(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID | None = None
) -> list[Attendance]:
    query = db.query(Attendance).filter(Attendance.company_id == company_id)
    if project_id:
        query = query.filter(Attendance.project_id == project_id)
    return query.order_by(Attendance.attendance_date.desc()).all()


def get_project_labor_cost(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> ProjectLaborCost:
    get_project(db, company_id, project_id)
    records = list_attendance(db, company_id, project_id)

    total_cost = Decimal("0")
    present_days = 0
    half_days = 0
    employee_ids: set[uuid.UUID] = set()

    # Cache wages so we don't re-query the same employee for every attendance row.
    wage_cache: dict[uuid.UUID, Decimal] = {}

    for record in records:
        employee_ids.add(record.employee_id)
        if record.employee_id not in wage_cache:
            employee = get_employee(db, company_id, record.employee_id)
            wage_cache[record.employee_id] = employee.daily_wage

        wage = wage_cache[record.employee_id]
        if record.status == AttendanceStatus.PRESENT:
            total_cost += wage
            present_days += 1
        elif record.status == AttendanceStatus.HALF_DAY:
            total_cost += wage / 2
            half_days += 1

    return ProjectLaborCost(
        project_id=project_id,
        total_labor_cost=total_cost,
        present_days=present_days,
        half_days=half_days,
        employee_count=len(employee_ids),
    )


def get_employee_productivity(
    db: Session, company_id: uuid.UUID, employee_id: uuid.UUID
) -> EmployeeProductivity:
    employee = get_employee(db, company_id, employee_id)
    records = (
        db.query(Attendance)
        .filter(Attendance.company_id == company_id, Attendance.employee_id == employee_id)
        .all()
    )

    total = len(records)
    present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    rate = (Decimal(present) / Decimal(total) * 100) if total > 0 else Decimal("0")

    return EmployeeProductivity(
        employee_id=employee_id,
        employee_name=employee.full_name,
        total_days_recorded=total,
        present_days=present,
        absent_days=absent,
        attendance_rate_percent=rate,
    )
