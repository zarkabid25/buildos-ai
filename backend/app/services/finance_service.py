import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import PurchaseOrderStatus
from app.models.expense import Expense, ExpenseCategory
from app.models.procurement import PurchaseOrder
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCreate, ProjectCostSummary
from app.services.project_service import get_project

# ---- Expense categories -----------------------------------------------------


def list_categories(db: Session, company_id: uuid.UUID) -> list[ExpenseCategory]:
    return (
        db.query(ExpenseCategory)
        .filter(ExpenseCategory.company_id == company_id)
        .order_by(ExpenseCategory.name.asc())
        .all()
    )


def create_category(db: Session, company_id: uuid.UUID, payload: ExpenseCategoryCreate) -> ExpenseCategory:
    category = ExpenseCategory(company_id=company_id, **payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


# ---- Expenses ----------------------------------------------------------------


def list_expenses(db: Session, company_id: uuid.UUID, project_id: uuid.UUID | None = None) -> list[Expense]:
    query = db.query(Expense).filter(Expense.company_id == company_id)
    if project_id:
        query = query.filter(Expense.project_id == project_id)
    return query.order_by(Expense.expense_date.desc()).all()


def create_expense(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, payload: ExpenseCreate
) -> Expense:
    get_project(db, company_id, payload.project_id)
    expense = Expense(company_id=company_id, created_by_id=user_id, **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


# ---- Project cost summary (BUILD-048, 051, 052, 053) -------------------------


def get_project_cost_summary(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> ProjectCostSummary:
    project = get_project(db, company_id, project_id)

    # "Committed" = value of every purchase order raised for this project that
    # hasn't been cancelled, whether or not goods have been received yet --
    # money that's earmarked the moment a PO is approved, not just when spent.
    pos = (
        db.query(PurchaseOrder)
        .filter(
            PurchaseOrder.company_id == company_id,
            PurchaseOrder.project_id == project_id,
            PurchaseOrder.status != PurchaseOrderStatus.CANCELLED,
        )
        .all()
    )
    committed = sum((po.total_amount for po in pos), Decimal("0"))

    # "Actual" = recorded expenses only (this MVP doesn't auto-create an expense
    # from a goods receipt, to avoid double-counting the same money as both
    # "committed" via the PO and "actual" via an auto-generated expense).
    expenses = list_expenses(db, company_id, project_id)
    actual = sum((e.amount for e in expenses), Decimal("0"))

    original_budget = Decimal(str(project.budget))
    remaining = original_budget - committed - actual

    # Forecast (estimate at completion): if we know how far along the project
    # is, project the total cost at the current spend-per-progress rate --
    # the same idea as earned-value cost forecasting, just the simplest
    # version of it. Without progress data there's nothing to extrapolate
    # from, so the forecast falls back to money already committed + spent.
    if project.progress_percent > 0:
        forecast = (actual / Decimal(project.progress_percent)) * 100
        forecast_basis = (
            f"Projected from {project.progress_percent}% progress and {actual} spent so far "
            f"(actual ÷ progress% × 100)."
        )
    else:
        forecast = committed + actual
        forecast_basis = "No progress recorded yet, so this is committed + actual spend, not a real projection."

    expected_variance = forecast - original_budget

    return ProjectCostSummary(
        original_budget=original_budget,
        committed=committed,
        actual=actual,
        remaining=remaining,
        forecast=forecast,
        expected_variance=expected_variance,
        forecast_basis=forecast_basis,
    )
