import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.project_member import ProjectMemberAdd, ProjectMemberWithUser
from app.services import project_member_service

router = APIRouter(prefix="/projects/{project_id}/members", tags=["project-members"])

CAN_MANAGE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER)


@router.get("", response_model=list[ProjectMemberWithUser])
def list_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectMemberWithUser]:
    return project_member_service.list_members(db, current_user.company_id, project_id)


@router.post("", response_model=ProjectMemberWithUser, status_code=201)
def add_member(
    project_id: uuid.UUID,
    payload: ProjectMemberAdd,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> ProjectMemberWithUser:
    return project_member_service.add_member(db, current_user.company_id, project_id, payload.user_id)


@router.delete("/{member_id}", status_code=204)
def remove_member(
    project_id: uuid.UUID,
    member_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    project_member_service.remove_member(db, current_user.company_id, project_id, member_id)
