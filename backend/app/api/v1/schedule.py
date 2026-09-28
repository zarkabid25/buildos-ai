import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import ProjectSchedule
from app.services import schedule_service

router = APIRouter(tags=["schedule"])


@router.get("/projects/{project_id}/schedule", response_model=ProjectSchedule)
def get_project_schedule(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectSchedule:
    return schedule_service.get_project_schedule(db, current_user.company_id, project_id)
