import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.workforce import (
    AttendanceCreate,
    AttendanceRead,
    EmployeeAssignmentCreate,
    EmployeeAssignmentRead,
    EmployeeCreate,
    EmployeeProductivity,
    EmployeeRead,
    EmployeeUpdate,
    ProjectLaborCost,
)
from app.services import workforce_service

router = APIRouter(tags=["workforce"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER)


@router.get("/employees", response_model=list[EmployeeRead])
def list_employees(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[EmployeeRead]:
    return workforce_service.list_employees(db, current_user.company_id)


@router.post("/employees", response_model=EmployeeRead, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EmployeeRead:
    return workforce_service.create_employee(db, current_user.company_id, payload)


@router.patch("/employees/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EmployeeRead:
    return workforce_service.update_employee(db, current_user.company_id, employee_id, payload)


@router.post("/employees/{employee_id}/assignments", response_model=EmployeeAssignmentRead, status_code=201)
def assign_to_project(
    employee_id: uuid.UUID,
    payload: EmployeeAssignmentCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> EmployeeAssignmentRead:
    return workforce_service.assign_to_project(db, current_user.company_id, employee_id, payload)


@router.get("/employees/{employee_id}/assignments", response_model=list[EmployeeAssignmentRead])
def list_project_assignments(
    employee_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmployeeAssignmentRead]:
    return workforce_service.list_project_assignments(db, current_user.company_id, employee_id)


@router.get("/employees/{employee_id}/productivity", response_model=EmployeeProductivity)
def get_employee_productivity(
    employee_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmployeeProductivity:
    return workforce_service.get_employee_productivity(db, current_user.company_id, employee_id)


@router.get("/attendance", response_model=list[AttendanceRead])
def list_attendance(
    project_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AttendanceRead]:
    return workforce_service.list_attendance(db, current_user.company_id, project_id)


@router.post("/attendance", response_model=AttendanceRead, status_code=201)
def record_attendance(
    payload: AttendanceCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE, UserRole.SITE_ENGINEER)),
    db: Session = Depends(get_db),
) -> AttendanceRead:
    return workforce_service.record_attendance(db, current_user.company_id, payload)


@router.get("/projects/{project_id}/labor-cost", response_model=ProjectLaborCost)
def get_project_labor_cost(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectLaborCost:
    return workforce_service.get_project_labor_cost(db, current_user.company_id, project_id)
