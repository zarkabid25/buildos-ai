import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])

CAN_WRITE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN, UserRole.PROJECT_MANAGER, UserRole.SITE_ENGINEER)


@router.get("", response_model=list[TaskRead])
def list_tasks(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskRead]:
    return task_service.list_tasks(db, current_user.company_id, project_id)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(
    project_id: uuid.UUID,
    payload: TaskCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> TaskRead:
    return task_service.create_task(db, current_user.company_id, project_id, payload)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskRead:
    # Any project member can update task status (e.g. move to done); field-level
    # restrictions beyond that are out of scope for the MVP task board.
    return task_service.update_task(db, current_user.company_id, project_id, task_id, payload)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    task_service.delete_task(db, current_user.company_id, project_id, task_id)
