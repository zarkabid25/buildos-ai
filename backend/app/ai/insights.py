"""Rules-based insights over a company's own data.

Nothing here calls a language model. Every insight comes from a fixed threshold
applied to numbers the services already compute, and carries the supporting
figures in `data`, so the same engine can drive the dashboard today and act as
a read-only tool for the copilot later. Thresholds live in the constants below.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import MaterialRequestStatus, PurchaseOrderStatus, TaskStatus
from app.models.material import Material
from app.models.milestone import Milestone
from app.models.procurement import MaterialRequest, PurchaseOrder
from app.models.task import Task
from app.schemas.ai import Insight, InsightsReport
from app.services import equipment_service, finance_service, forecast_service, project_service
from app.services.inventory_service import get_total_stock_on_hand

STOCKOUT_HIGH_DAYS = 3
STOCKOUT_MEDIUM_DAYS = 7
OVERRUN_HIGH_PERCENT = Decimal("10")

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _pct(part: Decimal, whole: Decimal) -> Decimal:
    return (part / whole * 100) if whole else Decimal("0")


def _project_insights(db: Session, company_id: uuid.UUID) -> list[Insight]:
    insights: list[Insight] = []
    today = date.today()

    for project in project_service.list_projects(db, company_id):
        health = project_service.get_health(db, company_id, project.id)
        if health.is_at_risk:
            insights.append(
                Insight(
                    severity="high" if (health.schedule_score or 100) < 50 else "medium",
                    category="schedule",
                    title=f"{project.name} is behind schedule",
                    detail=(
                        f"Reported progress is {project.progress_percent}% but the schedule is further along "
                        f"than that (schedule score {health.schedule_score}/100)."
                    ),
                    project_id=project.id,
                    data={"progress_percent": project.progress_percent, "schedule_score": health.schedule_score},
                )
            )

        # A cost forecast is only a real projection once progress has been recorded.
        if project.progress_percent > 0 and Decimal(str(project.budget)) > 0:
            cost = finance_service.get_project_cost_summary(db, company_id, project.id)
            if cost.expected_variance > 0:
                over_percent = _pct(cost.expected_variance, cost.original_budget)
                insights.append(
                    Insight(
                        severity="high" if over_percent >= OVERRUN_HIGH_PERCENT else "medium",
                        category="cost",
                        title=f"{project.name} is forecast to overrun its budget",
                        detail=(
                            f"Forecast {cost.forecast:,.0f} vs budget {cost.original_budget:,.0f} "
                            f"(+{over_percent:.1f}%). {cost.forecast_basis}"
                        ),
                        project_id=project.id,
                        data={
                            "forecast": str(cost.forecast),
                            "budget": str(cost.original_budget),
                            "expected_variance": str(cost.expected_variance),
                        },
                    )
                )

        overdue_tasks = (
            db.query(Task)
            .filter(
                Task.company_id == company_id,
                Task.project_id == project.id,
                Task.status != TaskStatus.DONE,
                Task.due_date.isnot(None),
                Task.due_date < today,
            )
            .count()
        )
        if overdue_tasks:
            insights.append(
                Insight(
                    severity="medium",
                    category="schedule",
                    title=f"{project.name} has {overdue_tasks} overdue task(s)",
                    detail="Tasks past their due date that aren't marked done.",
                    project_id=project.id,
                    data={"overdue_tasks": overdue_tasks},
                )
            )

        late_milestones = (
            db.query(Milestone)
            .filter(
                Milestone.company_id == company_id,
                Milestone.project_id == project.id,
                Milestone.is_completed.is_(False),
                Milestone.due_date.isnot(None),
                Milestone.due_date < today,
            )
            .count()
        )
        if late_milestones:
            insights.append(
                Insight(
                    severity="medium",
                    category="schedule",
                    title=f"{project.name} has {late_milestones} late milestone(s)",
                    detail="Milestones past their due date that aren't completed.",
                    project_id=project.id,
                    data={"late_milestones": late_milestones},
                )
            )

    return insights


def _inventory_insights(db: Session, company_id: uuid.UUID) -> list[Insight]:
    insights: list[Insight] = []

    for forecast in forecast_service.list_forecasts(db, company_id):
        if forecast.days_remaining is None or forecast.days_remaining > STOCKOUT_MEDIUM_DAYS:
            continue
        insights.append(
            Insight(
                severity="high" if forecast.days_remaining <= STOCKOUT_HIGH_DAYS else "medium",
                category="inventory",
                title=f"{forecast.material_name} may run out in {forecast.days_remaining} day(s)",
                detail=forecast.reason,
                data={
                    "material_id": str(forecast.material_id),
                    "current_stock": str(forecast.current_stock),
                    "daily_avg_usage": str(forecast.daily_avg_usage),
                    "recommended_order_quantity": (
                        str(forecast.recommended_order_quantity)
                        if forecast.recommended_order_quantity is not None
                        else None
                    ),
                },
            )
        )

    forecast_flagged = {i.data["material_id"] for i in insights}
    for material in db.query(Material).filter(Material.company_id == company_id).all():
        if material.reorder_point <= 0 or str(material.id) in forecast_flagged:
            continue
        stock = get_total_stock_on_hand(db, company_id, material.id)
        if stock <= material.reorder_point:
            insights.append(
                Insight(
                    severity="high" if stock <= 0 else "medium",
                    category="inventory",
                    title=f"{material.name} is {'out of stock' if stock <= 0 else 'at or below its reorder point'}",
                    detail=f"{stock} {material.unit} on hand; reorder point is {material.reorder_point}.",
                    data={"material_id": str(material.id), "current_stock": str(stock)},
                )
            )

    for anomaly in forecast_service.detect_anomalies(db, company_id):
        insights.append(
            Insight(
                severity="medium",
                category="inventory",
                title=f"Unusual {anomaly.material_name} consumption",
                detail=anomaly.message,
                data={"material_id": str(anomaly.material_id), "change_percent": str(round(anomaly.change_percent, 1))},
            )
        )
    return insights


def _operations_insights(db: Session, company_id: uuid.UUID) -> list[Insight]:
    insights: list[Insight] = []

    for reminder in equipment_service.get_maintenance_reminders(db, company_id):
        insights.append(
            Insight(
                severity="high" if reminder.is_overdue else "low",
                category="equipment",
                title=(
                    f"{reminder.equipment_name} maintenance is overdue"
                    if reminder.is_overdue
                    else f"{reminder.equipment_name} maintenance due in {reminder.days_until_due} day(s)"
                ),
                detail=f"Next maintenance due {reminder.next_due_date}.",
                data={"equipment_id": str(reminder.equipment_id), "days_until_due": reminder.days_until_due},
            )
        )

    pending_pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.company_id == company_id, PurchaseOrder.status == PurchaseOrderStatus.PENDING_APPROVAL)
        .count()
    )
    if pending_pos:
        insights.append(
            Insight(
                severity="medium",
                category="procurement",
                title=f"{pending_pos} purchase order(s) awaiting approval",
                detail="Goods can't be received against a PO until it's approved.",
                data={"pending_purchase_orders": pending_pos},
            )
        )

    pending_requests = (
        db.query(MaterialRequest)
        .filter(MaterialRequest.company_id == company_id, MaterialRequest.status == MaterialRequestStatus.PENDING)
        .count()
    )
    if pending_requests:
        insights.append(
            Insight(
                severity="low",
                category="procurement",
                title=f"{pending_requests} material request(s) not yet actioned",
                detail="Requests waiting to be approved or turned into a purchase order.",
                data={"pending_material_requests": pending_requests},
            )
        )
    return insights


def build_insights(db: Session, company_id: uuid.UUID) -> InsightsReport:
    insights = _project_insights(db, company_id) + _inventory_insights(db, company_id) + _operations_insights(db, company_id)
    insights.sort(key=lambda i: (_SEVERITY_RANK[i.severity], i.category, i.title))

    counts = {sev: sum(1 for i in insights if i.severity == sev) for sev in ("high", "medium", "low")}
    counts["total"] = len(insights)

    if not insights:
        summary = "Nothing needs attention right now."
    else:
        lead = "; ".join(i.title for i in insights[:3])
        summary = (
            f"{counts['total']} item(s) need attention ({counts['high']} high, {counts['medium']} medium, "
            f"{counts['low']} low). Most urgent: {lead}."
        )
    return InsightsReport(summary=summary, counts=counts, insights=insights)
