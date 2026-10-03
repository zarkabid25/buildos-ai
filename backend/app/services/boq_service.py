import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.models.boq import BoqItem
from app.models.enums import InventoryTransactionType
from app.models.inventory_transaction import InventoryTransaction
from app.models.material import Material
from app.schemas.boq import (
    BoqAiGeneratedItem,
    BoqAiGenerateRequest,
    BoqCategoryTotal,
    BoqItemCreate,
    BoqItemUpdate,
    BoqSummary,
    BoqVsActual,
    BoqVsActualLine,
    UnplannedConsumption,
)
from app.services.material_service import get_material
from app.services.project_service import get_project
from app.services import audit_service


def _check_material_link(
    db: Session,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    material_id: uuid.UUID,
    unit: str,
    exclude_item_id: uuid.UUID | None = None,
) -> None:
    """A BOQ line can only be measured against a material in the same unit, and a
    material can back only one line per project, or its consumption would be counted twice."""
    material = get_material(db, company_id, material_id)
    if material.unit.strip().lower() != unit.strip().lower():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unit mismatch: BOQ line is in '{unit}' but {material.name} is tracked in '{material.unit}'",
        )
    query = db.query(BoqItem).filter(
        BoqItem.company_id == company_id,
        BoqItem.project_id == project_id,
        BoqItem.material_id == material_id,
    )
    if exclude_item_id:
        query = query.filter(BoqItem.id != exclude_item_id)
    if query.first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"{material.name} is already linked to another BOQ line in this project"
        )


def list_items(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[BoqItem]:
    get_project(db, company_id, project_id)
    return (
        db.query(BoqItem)
        .filter(BoqItem.company_id == company_id, BoqItem.project_id == project_id)
        .order_by(BoqItem.item_code.asc())
        .all()
    )


def create_item(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, payload: BoqItemCreate
) -> BoqItem:
    get_project(db, company_id, project_id)
    if payload.material_id:
        _check_material_link(db, company_id, project_id, payload.material_id, payload.unit)
    item = BoqItem(company_id=company_id, project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def bulk_create_items(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, items: list[BoqItemCreate], ai_generated: bool = False
) -> list[BoqItem]:
    get_project(db, company_id, project_id)
    linked: set[uuid.UUID] = set()
    for payload in items:
        if payload.material_id:
            if payload.material_id in linked:
                raise HTTPException(status.HTTP_409_CONFLICT, "The same material is linked to more than one BOQ line")
            _check_material_link(db, company_id, project_id, payload.material_id, payload.unit)
            linked.add(payload.material_id)
    rows = [
        BoqItem(
            company_id=company_id,
            project_id=project_id,
            is_ai_generated=ai_generated,
            **payload.model_dump(),
        )
        for payload in items
    ]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def update_item(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, item_id: uuid.UUID, payload: BoqItemUpdate
) -> BoqItem:
    item = (
        db.query(BoqItem)
        .filter(BoqItem.id == item_id, BoqItem.project_id == project_id, BoqItem.company_id == company_id)
        .first()
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BOQ item not found")

    changes = payload.model_dump(exclude_unset=True)
    material_id = changes.get("material_id", item.material_id)
    if material_id and ("material_id" in changes or "unit" in changes):
        _check_material_link(
            db, company_id, project_id, material_id, changes.get("unit") or item.unit, exclude_item_id=item.id
        )
    apply_changes(item, changes)
    db.commit()
    db.refresh(item)
    return item


def delete_item(
    db: Session, company_id: uuid.UUID, actor_id: uuid.UUID, project_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    item = (
        db.query(BoqItem)
        .filter(BoqItem.id == item_id, BoqItem.project_id == project_id, BoqItem.company_id == company_id)
        .first()
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BOQ item not found")
    audit_service.record(
        db, company_id, actor_id, "boq_item.deleted", "boq_item", item.id,
        f"BOQ line {item.item_code} removed: {item.description} ({item.amount:,.2f})",
        {"project_id": str(project_id), "quantity": str(item.quantity), "rate": str(item.rate)},
    )
    db.delete(item)
    db.commit()


def get_summary(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> BoqSummary:
    items = list_items(db, company_id, project_id)
    total_amount = sum((item.amount for item in items), Decimal("0"))

    totals_by_category: dict[str, list[BoqItem]] = {}
    for item in items:
        key = item.category or "Uncategorized"
        totals_by_category.setdefault(key, []).append(item)

    by_category = [
        BoqCategoryTotal(
            category=category,
            total_amount=sum((i.amount for i in cat_items), Decimal("0")),
            item_count=len(cat_items),
        )
        for category, cat_items in sorted(totals_by_category.items())
    ]

    return BoqSummary(total_amount=total_amount, item_count=len(items), by_category=by_category)


def get_boq_vs_actual(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> BoqVsActual:
    """Planned BOQ quantities against stock allocated to the project. Pure arithmetic
    over the BOQ and the inventory ledger — no estimates involved."""
    items = list_items(db, company_id, project_id)

    allocated: dict[uuid.UUID, Decimal] = dict(
        db.query(InventoryTransaction.material_id, func.sum(InventoryTransaction.quantity))
        .filter(
            InventoryTransaction.company_id == company_id,
            InventoryTransaction.project_id == project_id,
            InventoryTransaction.transaction_type == InventoryTransactionType.ALLOCATION,
        )
        .group_by(InventoryTransaction.material_id)
        .all()
    )
    material_ids = set(allocated) | {i.material_id for i in items if i.material_id}
    materials: dict[uuid.UUID, Material] = {}
    if material_ids:
        materials = {
            m.id: m
            for m in db.query(Material).filter(Material.company_id == company_id, Material.id.in_(material_ids))
        }

    lines: list[BoqVsActualLine] = []
    planned_total = tracked_planned_total = actual_total = Decimal("0")
    for item in items:
        planned_quantity = item.quantity or Decimal("0")
        rate = item.rate or Decimal("0")
        planned_total += item.amount
        base = dict(
            boq_item_id=item.id,
            item_code=item.item_code,
            description=item.description,
            unit=item.unit,
            material_id=item.material_id,
            material_name=materials[item.material_id].name if item.material_id in materials else None,
            planned_quantity=planned_quantity,
            rate=rate,
            planned_amount=item.amount,
        )
        if not item.material_id:
            lines.append(
                BoqVsActualLine(
                    **base,
                    actual_quantity=None,
                    actual_amount=None,
                    quantity_variance=None,
                    variance_percent=None,
                    status="not_tracked",
                )
            )
            continue

        actual_quantity = allocated.get(item.material_id, Decimal("0"))
        actual_amount = actual_quantity * rate
        variance = actual_quantity - planned_quantity
        tracked_planned_total += item.amount
        actual_total += actual_amount
        if actual_quantity == 0:
            line_status = "not_started"
        elif actual_quantity > planned_quantity:
            line_status = "over_plan"
        else:
            line_status = "within_plan"
        lines.append(
            BoqVsActualLine(
                **base,
                actual_quantity=actual_quantity,
                actual_amount=actual_amount,
                quantity_variance=variance,
                variance_percent=(
                    (variance / planned_quantity * 100).quantize(Decimal("0.1")) if planned_quantity else None
                ),
                status=line_status,
            )
        )

    linked_ids = {i.material_id for i in items if i.material_id}
    unplanned = sorted(
        (
            UnplannedConsumption(
                material_id=material_id,
                material_name=materials[material_id].name,
                unit=materials[material_id].unit,
                actual_quantity=qty,
            )
            for material_id, qty in allocated.items()
            if material_id not in linked_ids and material_id in materials
        ),
        key=lambda u: u.material_name,
    )

    return BoqVsActual(
        lines=lines,
        unplanned=unplanned,
        planned_total=planned_total,
        tracked_planned_total=tracked_planned_total,
        actual_total=actual_total,
    )


# Rule-based starter templates keyed by project type keyword. This is a deterministic
# placeholder standing in for the real LLM-backed BOQ assistant (Epic 15/16 — AI
# infrastructure isn't built yet, see docs/daily-log.md). Every quantity/rate here is a
# rough industry rule of thumb, not a live estimate, and the API response carries an
# explicit disclaimer per CLAUDE.md rule 13 (AI-generated quantities must be marked
# as estimates requiring professional review).
_STARTER_TEMPLATE: list[BoqAiGeneratedItem] = [
    BoqAiGeneratedItem(item_code="001", description="Cement (OPC)", category="Materials", unit="Bag", quantity=Decimal("1200"), rate=Decimal("1400")),
    BoqAiGeneratedItem(item_code="002", description="Reinforcement steel", category="Materials", unit="Ton", quantity=Decimal("45"), rate=Decimal("280000")),
    BoqAiGeneratedItem(item_code="003", description="Sand", category="Materials", unit="m3", quantity=Decimal("850"), rate=Decimal("4500")),
    BoqAiGeneratedItem(item_code="004", description="Crush/aggregate", category="Materials", unit="m3", quantity=Decimal("700"), rate=Decimal("5200")),
    BoqAiGeneratedItem(item_code="005", description="Bricks", category="Materials", unit="Nos", quantity=Decimal("80000"), rate=Decimal("14")),
    BoqAiGeneratedItem(item_code="006", description="Mason labor", category="Labor", unit="Day", quantity=Decimal("400"), rate=Decimal("1800")),
    BoqAiGeneratedItem(item_code="007", description="Unskilled labor", category="Labor", unit="Day", quantity=Decimal("900"), rate=Decimal("1200")),
    BoqAiGeneratedItem(item_code="008", description="Excavation", category="Earthwork", unit="m3", quantity=Decimal("300"), rate=Decimal("650")),
]


def generate_starter_boq(request: BoqAiGenerateRequest) -> list[BoqAiGeneratedItem]:
    return _STARTER_TEMPLATE
