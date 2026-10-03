"""Read-only reports (BUILD-108..111). Every figure is plain arithmetic over existing
records, reusing the same service functions the rest of the app uses, so a report
can never disagree with the screen it summarises."""

import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.enums import InventoryTransactionType, TaskStatus
from app.models.expense import Expense, ExpenseCategory
from app.models.inventory_transaction import InventoryTransaction
from app.models.material import Material
from app.models.procurement import MaterialRequest, PurchaseOrder
from app.models.project import Project
from app.models.supplier import Supplier
from app.models.task import Task
from app.schemas.report import (
    ExpenseReport,
    ExpenseReportRow,
    InventoryReport,
    InventoryReportRow,
    ProcurementReport,
    ProjectReport,
    ProjectReportRow,
    SupplierSpendRow,
)
from app.services import finance_service, inventory_service, project_service

_RECEIVED = (InventoryTransactionType.STOCK_IN,)
_ISSUED = (InventoryTransactionType.STOCK_OUT, InventoryTransactionType.ALLOCATION)


def _check_range(date_from: date | None, date_to: date | None) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from must be on or before date_to")


def _utc_bounds(date_from: date | None, date_to: date | None) -> tuple[datetime | None, datetime | None]:
    """Whole UTC days, date_to inclusive, for filtering created_at timestamps."""
    start = datetime.combine(date_from, time.min, tzinfo=timezone.utc) if date_from else None
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc) if date_to else None
    return start, end


def project_report(db: Session, company_id: uuid.UUID, today: date | None = None) -> ProjectReport:
    today = today or date.today()
    projects = project_service.list_projects(db, company_id)

    task_counts: dict[uuid.UUID, tuple[int, int]] = defaultdict(lambda: (0, 0))
    open_tasks = (
        db.query(Task.project_id, Task.due_date)
        .filter(Task.company_id == company_id, Task.status != TaskStatus.DONE)
        .all()
    )
    for project_id, due in open_tasks:
        open_count, overdue = task_counts[project_id]
        task_counts[project_id] = (open_count + 1, overdue + (1 if due and due < today else 0))

    rows = []
    for project in projects:
        cost = finance_service.get_project_cost_summary(db, company_id, project.id)
        health = project_service.get_health(db, company_id, project.id)
        open_count, overdue = task_counts[project.id]
        rows.append(
            ProjectReportRow(
                project_id=project.id,
                name=project.name,
                code=project.code,
                status=project.status,
                progress_percent=project.progress_percent,
                budget=cost.original_budget,
                committed=cost.committed,
                actual=cost.actual,
                forecast=cost.forecast,
                expected_variance=cost.expected_variance,
                schedule_variance_days=project_service.get_schedule_variance_days(project, today),
                health_score=health.overall_score,
                open_tasks=open_count,
                overdue_tasks=overdue,
            )
        )
    return ProjectReport(
        as_of=today,
        rows=rows,
        total_budget=sum((r.budget for r in rows), Decimal("0")),
        total_actual=sum((r.actual for r in rows), Decimal("0")),
        total_committed=sum((r.committed for r in rows), Decimal("0")),
    )


def inventory_report(
    db: Session, company_id: uuid.UUID, date_from: date | None = None, date_to: date | None = None
) -> InventoryReport:
    _check_range(date_from, date_to)
    start, end = _utc_bounds(date_from, date_to)

    query = db.query(
        InventoryTransaction.material_id,
        InventoryTransaction.transaction_type,
        func.sum(InventoryTransaction.quantity),
    ).filter(InventoryTransaction.company_id == company_id)
    if start:
        query = query.filter(InventoryTransaction.created_at >= start)
    if end:
        query = query.filter(InventoryTransaction.created_at < end)
    movements: dict[uuid.UUID, dict[str, Decimal]] = defaultdict(lambda: {"received": Decimal("0"), "issued": Decimal("0")})
    for material_id, tx_type, qty in query.group_by(InventoryTransaction.material_id, InventoryTransaction.transaction_type):
        if tx_type in _RECEIVED:
            movements[material_id]["received"] += qty
        elif tx_type in _ISSUED:
            movements[material_id]["issued"] += qty
        # Transfers move stock between warehouses; they don't change the company total.

    rows = []
    for material in db.query(Material).filter(Material.company_id == company_id).order_by(Material.name.asc()):
        # On hand is always "now", whatever the period: it's a balance, not a movement.
        on_hand = inventory_service.get_total_stock_on_hand(db, company_id, material.id)
        if on_hand <= 0:
            stock_status = "out"
        elif on_hand <= material.reorder_point:
            stock_status = "low"
        else:
            stock_status = "ok"
        rows.append(
            InventoryReportRow(
                material_id=material.id,
                name=material.name,
                sku=material.sku,
                unit=material.unit,
                on_hand=on_hand,
                reorder_point=material.reorder_point,
                stock_status=stock_status,
                received=movements[material.id]["received"],
                issued=movements[material.id]["issued"],
            )
        )
    return InventoryReport(
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        low_stock_count=sum(1 for r in rows if r.stock_status == "low"),
        out_of_stock_count=sum(1 for r in rows if r.stock_status == "out"),
    )


def procurement_report(
    db: Session, company_id: uuid.UUID, date_from: date | None = None, date_to: date | None = None
) -> ProcurementReport:
    _check_range(date_from, date_to)
    start, end = _utc_bounds(date_from, date_to)

    po_query = db.query(PurchaseOrder).options(joinedload(PurchaseOrder.items)).filter(
        PurchaseOrder.company_id == company_id
    )
    mr_query = db.query(MaterialRequest.status, func.count(MaterialRequest.id)).filter(
        MaterialRequest.company_id == company_id
    )
    if start:
        po_query = po_query.filter(PurchaseOrder.created_at >= start)
        mr_query = mr_query.filter(MaterialRequest.created_at >= start)
    if end:
        po_query = po_query.filter(PurchaseOrder.created_at < end)
        mr_query = mr_query.filter(MaterialRequest.created_at < end)
    pos = po_query.all()

    count_by_status: dict[str, int] = defaultdict(int)
    value_by_status: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_supplier: dict[uuid.UUID, list[PurchaseOrder]] = defaultdict(list)
    for po in pos:
        count_by_status[po.status.value] += 1
        value_by_status[po.status.value] += po.total_amount
        by_supplier[po.supplier_id].append(po)

    names = {}
    if by_supplier:
        names = dict(
            db.query(Supplier.id, Supplier.name).filter(Supplier.company_id == company_id, Supplier.id.in_(by_supplier))
        )
    rows = [
        SupplierSpendRow(
            supplier_id=supplier_id,
            supplier_name=names.get(supplier_id, "Unknown supplier"),
            po_count=len(supplier_pos),
            ordered_amount=sum((po.total_amount for po in supplier_pos), Decimal("0")),
            received_amount=sum(
                (i.quantity_received * i.rate for po in supplier_pos for i in po.items), Decimal("0")
            ),
        )
        for supplier_id, supplier_pos in by_supplier.items()
    ]
    rows.sort(key=lambda r: r.ordered_amount, reverse=True)

    return ProcurementReport(
        date_from=date_from,
        date_to=date_to,
        po_count_by_status=dict(count_by_status),
        po_value_by_status=dict(value_by_status),
        material_requests_by_status={s.value: n for s, n in mr_query.group_by(MaterialRequest.status)},
        rows=rows,
    )


def expense_report(
    db: Session, company_id: uuid.UUID, date_from: date | None = None, date_to: date | None = None
) -> ExpenseReport:
    _check_range(date_from, date_to)
    query = (
        db.query(Project.id, Project.name, ExpenseCategory.name, func.count(Expense.id), func.sum(Expense.amount))
        .join(Project, Project.id == Expense.project_id)
        .outerjoin(
            ExpenseCategory,
            (ExpenseCategory.id == Expense.category_id) & (ExpenseCategory.company_id == company_id),
        )
        .filter(Expense.company_id == company_id, Project.company_id == company_id)
    )
    # expense_date is a plain date, so no timezone conversion is involved here.
    if date_from:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to:
        query = query.filter(Expense.expense_date <= date_to)

    rows = [
        ExpenseReportRow(
            project_id=project_id,
            project_name=project_name,
            category=category or "Uncategorized",
            expense_count=count,
            amount=amount,
        )
        for project_id, project_name, category, count, amount in query.group_by(
            Project.id, Project.name, ExpenseCategory.name
        )
    ]
    rows.sort(key=lambda r: (r.project_name, r.category))

    by_category: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in rows:
        by_category[r.category] += r.amount

    return ExpenseReport(
        date_from=date_from,
        date_to=date_to,
        rows=rows,
        total_amount=sum((r.amount for r in rows), Decimal("0")),
        by_category=dict(by_category),
    )
