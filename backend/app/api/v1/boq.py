import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.boq import (
    BoqAiGenerateRequest,
    BoqAiGenerateResponse,
    BoqItemCreate,
    BoqItemRead,
    BoqItemUpdate,
    BoqSummary,
)
from app.services import boq_service

router = APIRouter(prefix="/projects/{project_id}/boq", tags=["boq"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER, UserRole.SITE_ENGINEER)


@router.get("", response_model=list[BoqItemRead])
def list_items(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BoqItemRead]:
    return boq_service.list_items(db, current_user.company_id, project_id)


@router.get("/summary", response_model=BoqSummary)
def boq_summary(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BoqSummary:
    return boq_service.get_summary(db, current_user.company_id, project_id)


@router.post("", response_model=BoqItemRead, status_code=201)
def create_item(
    project_id: uuid.UUID,
    payload: BoqItemCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> BoqItemRead:
    return boq_service.create_item(db, current_user.company_id, project_id, payload)


@router.patch("/{item_id}", response_model=BoqItemRead)
def update_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: BoqItemUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> BoqItemRead:
    return boq_service.update_item(db, current_user.company_id, project_id, item_id, payload)


@router.delete("/{item_id}", status_code=204)
def delete_item(
    project_id: uuid.UUID,
    item_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    boq_service.delete_item(db, current_user.company_id, project_id, item_id)


@router.post("/ai-generate", response_model=BoqAiGenerateResponse)
def ai_generate_boq(
    project_id: uuid.UUID,
    payload: BoqAiGenerateRequest,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
) -> BoqAiGenerateResponse:
    # Draft only — nothing is written to the database here. The user reviews the
    # generated items and calls POST /boq/ai-accept to actually create them, per
    # the AI-never-writes-directly rule in CLAUDE.md.
    items = boq_service.generate_starter_boq(payload)
    return BoqAiGenerateResponse(items=items)


@router.post("/ai-accept", response_model=list[BoqItemRead], status_code=201)
def ai_accept_boq(
    project_id: uuid.UUID,
    items: list[BoqItemCreate],
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> list[BoqItemRead]:
    return boq_service.bulk_create_items(
        db, current_user.company_id, project_id, items, ai_generated=True
    )
