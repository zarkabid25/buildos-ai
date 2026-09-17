import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.milestone import Milestone
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate
from app.services.project_service import get_project


def list_milestones(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[Milestone]:
    get_project(db, company_id, project_id)
    return (
        db.query(Milestone)
        .filter(Milestone.company_id == company_id, Milestone.project_id == project_id)
        .order_by(Milestone.due_date.asc().nulls_last())
        .all()
    )


def create_milestone(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, payload: MilestoneCreate
) -> Milestone:
    get_project(db, company_id, project_id)
    milestone = Milestone(company_id=company_id, project_id=project_id, **payload.model_dump())
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def update_milestone(
    db: Session,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    payload: MilestoneUpdate,
) -> Milestone:
    milestone = (
        db.query(Milestone)
        .filter(
            Milestone.id == milestone_id,
            Milestone.project_id == project_id,
            Milestone.company_id == company_id,
        )
        .first()
    )
    if not milestone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Milestone not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_completed") and not milestone.is_completed and "completed_date" not in updates:
        updates["completed_date"] = date.today()

    for field, value in updates.items():
        setattr(milestone, field, value)
    db.commit()
    db.refresh(milestone)
    return milestone
