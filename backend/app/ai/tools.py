"""The only things the assistant can do.

Rules this module enforces (CLAUDE.md, "AI safety architecture"):
- Every tool runs through the existing service layer with the *authenticated
  user's* company_id. company_id is never part of a tool's input schema, so the
  model cannot ask for another company's data.
- Every tool is read-only except `propose_material_request`, which only stores a
  draft proposal. A person has to approve it before anything real is created.
- Failures come back as error results the model can read, not exceptions.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.insights import build_insights
from app.models.enums import DocumentCategory, MaterialRequestStatus, PurchaseOrderStatus
from app.models.user import User
from app.services import (
    ai_proposal_service,
    daily_report_service,
    document_service,
    finance_service,
    forecast_service,
    inventory_service,
    material_service,
    procurement_service,
    project_service,
    workforce_service,
)

logger = logging.getLogger(__name__)

MAX_LIST_ITEMS = 25


class ToolInputError(Exception):
    pass


@dataclass
class ToolContext:
    db: Session
    company_id: uuid.UUID
    user: User
    conversation_id: uuid.UUID | None = None
    proposal_ids: list[uuid.UUID] = field(default_factory=list)


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[ToolContext, dict[str, Any]], Any]


def _uuid(args: dict[str, Any], key: str, required: bool = True) -> uuid.UUID | None:
    value = args.get(key)
    if value in (None, ""):
        if required:
            raise ToolInputError(f"'{key}' is required")
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise ToolInputError(f"'{key}' must be a valid id from one of the list tools")


def _enum(enum_cls, args: dict[str, Any], key: str):
    value = args.get(key)
    if value in (None, ""):
        return None
    try:
        return enum_cls(value)
    except ValueError:
        raise ToolInputError(f"'{key}' must be one of: {', '.join(e.value for e in enum_cls)}")


def _cap(items: list[Any]) -> dict[str, Any]:
    """Keep results small; tell the model when something was cut off."""
    return {
        "items": items[:MAX_LIST_ITEMS],
        "total_count": len(items),
        "truncated": len(items) > MAX_LIST_ITEMS,
    }


def _pick(obj: Any, fields: list[str]) -> dict[str, Any]:
    return {f: getattr(obj, f) for f in fields}


# ---- read-only tools ---------------------------------------------------------


def _list_projects(ctx: ToolContext, args: dict[str, Any]) -> Any:
    projects = project_service.list_projects(ctx.db, ctx.company_id)
    fields = ["id", "name", "code", "status", "progress_percent", "budget", "start_date", "end_date", "client_name"]
    return _cap([_pick(p, fields) for p in projects])


def _get_project_overview(ctx: ToolContext, args: dict[str, Any]) -> Any:
    project_id = _uuid(args, "project_id")
    project = project_service.get_project(ctx.db, ctx.company_id, project_id)
    return {
        "project": _pick(
            project,
            ["id", "name", "code", "status", "progress_percent", "budget", "start_date", "end_date", "location", "client_name"],
        ),
        "health": project_service.get_health(ctx.db, ctx.company_id, project_id).model_dump(mode="json"),
        "costs": finance_service.get_project_cost_summary(ctx.db, ctx.company_id, project_id).model_dump(mode="json"),
        "labor": workforce_service.get_project_labor_cost(ctx.db, ctx.company_id, project_id).model_dump(mode="json"),
    }


def _list_materials(ctx: ToolContext, args: dict[str, Any]) -> Any:
    materials = material_service.list_materials(ctx.db, ctx.company_id)
    return _cap([_pick(m, ["id", "name", "sku", "unit", "reorder_point"]) for m in materials])


def _get_inventory_status(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return {
        "dashboard": inventory_service.get_dashboard(ctx.db, ctx.company_id).model_dump(mode="json"),
        "forecasts": _cap([f.model_dump(mode="json") for f in forecast_service.list_forecasts(ctx.db, ctx.company_id)]),
    }


def _get_stock_levels(ctx: ToolContext, args: dict[str, Any]) -> Any:
    levels = inventory_service.list_stock_levels(ctx.db, ctx.company_id)
    return _cap([lvl.model_dump(mode="json") for lvl in levels])


def _get_consumption_anomalies(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return _cap([a.model_dump(mode="json") for a in forecast_service.detect_anomalies(ctx.db, ctx.company_id)])


def _list_purchase_orders(ctx: ToolContext, args: dict[str, Any]) -> Any:
    wanted = _enum(PurchaseOrderStatus, args, "status")
    pos = procurement_service.list_purchase_orders(ctx.db, ctx.company_id)
    if wanted:
        pos = [p for p in pos if p.status == wanted]
    return _cap([_pick(p, ["id", "po_number", "status", "supplier_id", "project_id", "total_amount"]) for p in pos])


def _list_material_requests(ctx: ToolContext, args: dict[str, Any]) -> Any:
    wanted = _enum(MaterialRequestStatus, args, "status")
    requests = procurement_service.list_material_requests(ctx.db, ctx.company_id)
    if wanted:
        requests = [r for r in requests if r.status == wanted]
    return _cap(
        [
            {
                "id": r.id,
                "project_id": r.project_id,
                "status": r.status,
                "items": [{"material_id": i.material_id, "quantity": i.quantity} for i in r.items],
            }
            for r in requests
        ]
    )


def _list_daily_reports(ctx: ToolContext, args: dict[str, Any]) -> Any:
    project_id = _uuid(args, "project_id")
    reports = daily_report_service.list_reports(ctx.db, ctx.company_id, project_id)
    fields = ["report_date", "weather", "workers_count", "work_completed", "materials_consumed", "problems", "notes"]
    return _cap([_pick(r, fields) for r in reports[:10]])


def _list_documents(ctx: ToolContext, args: dict[str, Any]) -> Any:
    docs = document_service.list_documents(
        ctx.db, ctx.company_id, _uuid(args, "project_id", required=False), _enum(DocumentCategory, args, "category")
    )
    # Metadata only. The assistant can say what exists, not read file contents.
    return _cap([_pick(d, ["id", "title", "category", "original_filename", "project_id", "description"]) for d in docs])


def _get_company_insights(ctx: ToolContext, args: dict[str, Any]) -> Any:
    return build_insights(ctx.db, ctx.company_id).model_dump(mode="json")


# ---- the one write-ish tool: creates a draft only ----------------------------


def _propose_material_request(ctx: ToolContext, args: dict[str, Any]) -> Any:
    items = args.get("items")
    if not isinstance(items, list) or not items:
        raise ToolInputError("'items' must be a non-empty list of {material_id, quantity}")
    proposal = ai_proposal_service.create_material_request_proposal(
        ctx.db,
        ctx.company_id,
        ctx.user,
        ctx.conversation_id,
        _uuid(args, "project_id"),
        items,
        args.get("notes"),
    )
    ctx.proposal_ids.append(proposal.id)
    return {
        "proposal_id": proposal.id,
        "status": proposal.status,
        "summary": proposal.summary,
        "message": (
            "Draft saved. It has NOT been submitted: a person must review and approve it in the "
            "AI Command Center before any material request exists. Tell the user that."
        ),
    }


_ID_NOTE = "Ids come from the list tools; never invent one."

TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("list_projects", "List all projects with status, progress, budget and dates.",
             {"type": "object", "properties": {}}, _list_projects),
        Tool("get_project_overview",
             "Health scores, cost summary (budget, committed, actual, forecast, variance) and labor cost for one project. " + _ID_NOTE,
             {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
             _get_project_overview),
        Tool("list_materials", "List materials (id, name, unit, reorder point). Use this to find material ids.",
             {"type": "object", "properties": {}}, _list_materials),
        Tool("get_inventory_status",
             "Inventory dashboard counts plus, per material, current stock, daily usage, estimated days to stockout and a reorder suggestion.",
             {"type": "object", "properties": {}}, _get_inventory_status),
        Tool("get_stock_levels", "Current quantity on hand per material per warehouse.",
             {"type": "object", "properties": {}}, _get_stock_levels),
        Tool("get_consumption_anomalies", "Materials whose recent consumption is unusually high versus their baseline.",
             {"type": "object", "properties": {}}, _get_consumption_anomalies),
        Tool("list_purchase_orders", "List purchase orders, optionally filtered by status.",
             {"type": "object", "properties": {"status": {"type": "string", "enum": [e.value for e in PurchaseOrderStatus]}}},
             _list_purchase_orders),
        Tool("list_material_requests", "List material requests, optionally filtered by status.",
             {"type": "object", "properties": {"status": {"type": "string", "enum": [e.value for e in MaterialRequestStatus]}}},
             _list_material_requests),
        Tool("list_daily_reports", "The 10 most recent daily site reports for a project. " + _ID_NOTE,
             {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": ["project_id"]},
             _list_daily_reports),
        Tool("list_documents", "List document metadata (titles, categories, filenames), optionally by project or category. Cannot read file contents.",
             {"type": "object", "properties": {
                 "project_id": {"type": "string"},
                 "category": {"type": "string", "enum": [e.value for e in DocumentCategory]}}},
             _list_documents),
        Tool("get_company_insights",
             "Rules-based list of current issues across the company (schedule, cost, inventory, equipment, procurement) with supporting numbers.",
             {"type": "object", "properties": {}}, _get_company_insights),
        Tool("propose_material_request",
             "Draft a material request for a person to approve. Does NOT create the request. Quantities are estimates the user must check. " + _ID_NOTE,
             {"type": "object",
              "properties": {
                  "project_id": {"type": "string"},
                  "items": {"type": "array", "items": {"type": "object",
                            "properties": {"material_id": {"type": "string"}, "quantity": {"type": "number"}},
                            "required": ["material_id", "quantity"]}},
                  "notes": {"type": "string"}},
              "required": ["project_id", "items"]},
             _propose_material_request),
    ]
}


def tool_schemas() -> list[dict[str, Any]]:
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in TOOLS.values()]


def run_tool(ctx: ToolContext, name: str, args: dict[str, Any]) -> tuple[str, bool]:
    """Returns (json_text, is_error). Never raises."""
    tool = TOOLS.get(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool '{name}'"}), True
    if not isinstance(args, dict):
        return json.dumps({"error": "Tool input must be an object"}), True
    try:
        return json.dumps(tool.handler(ctx, args), default=str), False
    except ToolInputError as exc:
        ctx.db.rollback()
        return json.dumps({"error": str(exc)}), True
    except HTTPException as exc:
        ctx.db.rollback()
        # 404s here also cover ids belonging to another company; don't distinguish.
        return json.dumps({"error": str(exc.detail)}), True
    except Exception:  # noqa: BLE001 - a tool bug must not take down the chat
        ctx.db.rollback()
        logger.exception("AI tool %s failed", name)
        return json.dumps({"error": "The tool failed unexpectedly"}), True
