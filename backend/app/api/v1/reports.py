import csv
import io
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import ExpenseReport, InventoryReport, ProcurementReport, ProjectReport
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])

Format = Literal["json", "csv"]


def _csv(rows: list[BaseModel], filename: str) -> Response:
    """The report's row table as CSV; totals stay in the JSON form."""
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0].model_dump(mode="json")))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump(mode="json"))
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
    )


@router.get("/projects", response_model=ProjectReport)
def project_report(
    format: Format = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.project_report(db, current_user.company_id)
    return _csv(report.rows, f"project-report-{report.as_of}") if format == "csv" else report


@router.get("/inventory", response_model=InventoryReport)
def inventory_report(
    date_from: date | None = None,
    date_to: date | None = None,
    format: Format = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.inventory_report(db, current_user.company_id, date_from, date_to)
    return _csv(report.rows, "inventory-report") if format == "csv" else report


@router.get("/procurement", response_model=ProcurementReport)
def procurement_report(
    date_from: date | None = None,
    date_to: date | None = None,
    format: Format = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.procurement_report(db, current_user.company_id, date_from, date_to)
    return _csv(report.rows, "procurement-report") if format == "csv" else report


@router.get("/expenses", response_model=ExpenseReport)
def expense_report(
    date_from: date | None = None,
    date_to: date | None = None,
    format: Format = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.expense_report(db, current_user.company_id, date_from, date_to)
    return _csv(report.rows, "expense-report") if format == "csv" else report
