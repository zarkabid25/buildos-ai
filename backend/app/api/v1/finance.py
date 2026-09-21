import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.expense import (
    ExpenseCategoryCreate,
    ExpenseCategoryRead,
    ExpenseCreate,
    ExpenseRead,
    ProjectCostSummary,
)
from app.services import finance_service

router = APIRouter(tags=["finance"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.ACCOUNTANT, UserRole.PROJECT_MANAGER)


@router.get("/expense-categories", response_model=list[ExpenseCategoryRead])
def list_categories(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ExpenseCategoryRead]:
    return finance_service.list_categories(db, current_user.company_id)


@router.post("/expense-categories", response_model=ExpenseCategoryRead, status_code=201)
def create_category(
    payload: ExpenseCategoryCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> ExpenseCategoryRead:
    return finance_service.create_category(db, current_user.company_id, payload)


@router.get("/expenses", response_model=list[ExpenseRead])
def list_expenses(
    project_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExpenseRead]:
    return finance_service.list_expenses(db, current_user.company_id, project_id)


@router.post("/expenses", response_model=ExpenseRead, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> ExpenseRead:
    return finance_service.create_expense(db, current_user.company_id, current_user.id, payload)


@router.get("/projects/{project_id}/cost-summary", response_model=ProjectCostSummary)
def get_project_cost_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectCostSummary:
    return finance_service.get_project_cost_summary(db, current_user.company_id, project_id)
