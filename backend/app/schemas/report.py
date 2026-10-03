import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import ProjectStatus


class ProjectReportRow(BaseModel):
    project_id: uuid.UUID
    name: str
    code: str
    status: ProjectStatus
    progress_percent: int
    budget: Decimal
    committed: Decimal
    actual: Decimal
    forecast: Decimal
    expected_variance: Decimal
    schedule_variance_days: int | None
    health_score: int | None
    open_tasks: int
    overdue_tasks: int


class ProjectReport(BaseModel):
    as_of: date
    rows: list[ProjectReportRow]
    total_budget: Decimal
    total_actual: Decimal
    total_committed: Decimal


class InventoryReportRow(BaseModel):
    material_id: uuid.UUID
    name: str
    sku: str
    unit: str
    on_hand: Decimal
    reorder_point: int
    stock_status: str  # "ok", "low" or "out"
    received: Decimal  # stock-in + goods receipts in the period
    issued: Decimal  # stock-out + project allocations in the period


class InventoryReport(BaseModel):
    date_from: date | None
    date_to: date | None
    rows: list[InventoryReportRow]
    low_stock_count: int
    out_of_stock_count: int


class SupplierSpendRow(BaseModel):
    supplier_id: uuid.UUID
    supplier_name: str
    po_count: int
    ordered_amount: Decimal
    received_amount: Decimal


class ProcurementReport(BaseModel):
    date_from: date | None
    date_to: date | None
    po_count_by_status: dict[str, int]
    po_value_by_status: dict[str, Decimal]
    material_requests_by_status: dict[str, int]
    rows: list[SupplierSpendRow]


class ExpenseReportRow(BaseModel):
    project_id: uuid.UUID
    project_name: str
    category: str
    expense_count: int
    amount: Decimal


class ExpenseReport(BaseModel):
    date_from: date | None
    date_to: date | None
    rows: list[ExpenseReportRow]
    total_amount: Decimal
    by_category: dict[str, Decimal]
