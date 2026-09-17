import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.milestone import MilestoneCreate, MilestoneRead, MilestoneUpdate
from app.services import milestone_service

router = APIRouter(prefix="/projects/{project_id}/milestones", tags=["milestones"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER, UserRole.SITE_ENGINEER)


@router.get("", response_model=list[MilestoneRead])
def list_milestones(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MilestoneRead]:
    return milestone_service.list_milestones(db, current_user.company_id, project_id)


@router.post("", response_model=MilestoneRead, status_code=201)
def create_milestone(
    project_id: uuid.UUID,
    payload: MilestoneCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> MilestoneRead:
    return milestone_service.create_milestone(db, current_user.company_id, project_id, payload)


@router.patch("/{milestone_id}", response_model=MilestoneRead)
def update_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    payload: MilestoneUpdate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> MilestoneRead:
    return milestone_service.update_milestone(
        db, current_user.company_id, project_id, milestone_id, payload
    )
