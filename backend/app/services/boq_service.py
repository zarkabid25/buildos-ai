import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.boq import BoqItem
from app.schemas.boq import (
    BoqAiGeneratedItem,
    BoqAiGenerateRequest,
    BoqCategoryTotal,
    BoqItemCreate,
    BoqItemUpdate,
    BoqSummary,
)
from app.services.project_service import get_project


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
    item = BoqItem(company_id=company_id, project_id=project_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def bulk_create_items(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, items: list[BoqItemCreate], ai_generated: bool = False
) -> list[BoqItem]:
    get_project(db, company_id, project_id)
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

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, company_id: uuid.UUID, project_id: uuid.UUID, item_id: uuid.UUID) -> None:
    item = (
        db.query(BoqItem)
        .filter(BoqItem.id == item_id, BoqItem.project_id == project_id, BoqItem.company_id == company_id)
        .first()
    )
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "BOQ item not found")
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
