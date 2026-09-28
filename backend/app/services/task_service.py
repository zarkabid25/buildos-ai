import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import NotificationType
from app.models.task import Task, TaskDependency
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import notification_service
from app.services.project_service import get_project


def list_tasks(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[Task]:
    get_project(db, company_id, project_id)
    return (
        db.query(Task)
        .filter(Task.company_id == company_id, Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .all()
    )


def get_task(db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id, Task.company_id == company_id)
        .first()
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return task


def create_task(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, actor_id: uuid.UUID, payload: TaskCreate
) -> Task:
    project = get_project(db, company_id, project_id)
    task = Task(company_id=company_id, project_id=project_id, **payload.model_dump())
    db.add(task)
    db.flush()

    if task.assignee_id and task.assignee_id != actor_id:
        notification_service.create_notification(
            db, company_id, task.assignee_id, NotificationType.TASK_ASSIGNED,
            title=f"You were assigned: {task.title}",
            body=f"Project: {project.name}",
            link=f"/projects/{project_id}",
        )

    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session,
    company_id: uuid.UUID,
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: TaskUpdate,
) -> Task:
    task = get_task(db, company_id, project_id, task_id)
    updates = payload.model_dump(exclude_unset=True)
    previous_assignee = task.assignee_id

    for field, value in updates.items():
        setattr(task, field, value)

    newly_assigned = (
        "assignee_id" in updates
        and task.assignee_id
        and task.assignee_id != previous_assignee
        and task.assignee_id != actor_id
    )
    if newly_assigned:
        project = get_project(db, company_id, project_id)
        notification_service.create_notification(
            db, company_id, task.assignee_id, NotificationType.TASK_ASSIGNED,
            title=f"You were assigned: {task.title}",
            body=f"Project: {project.name}",
            link=f"/projects/{project_id}",
        )

    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = get_task(db, company_id, project_id, task_id)
    db.delete(task)
    db.commit()


def _depends_transitively(db: Session, company_id: uuid.UUID, start_task_id: uuid.UUID, target_id: uuid.UUID) -> bool:
    """True if start_task_id already (directly or indirectly) depends on target_id."""
    seen: set[uuid.UUID] = set()
    stack = [start_task_id]
    while stack:
        current = stack.pop()
        if current == target_id:
            return True
        if current in seen:
            continue
        seen.add(current)
        links = (
            db.query(TaskDependency.depends_on_task_id)
            .filter(TaskDependency.company_id == company_id, TaskDependency.task_id == current)
            .all()
        )
        stack.extend(dep_id for (dep_id,) in links)
    return False


def add_dependency(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID, depends_on_task_id: uuid.UUID
) -> Task:
    task = get_task(db, company_id, project_id, task_id)
    depends_on = get_task(db, company_id, project_id, depends_on_task_id)  # must be same project

    if task.id == depends_on.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A task cannot depend on itself")

    existing = (
        db.query(TaskDependency)
        .filter(
            TaskDependency.company_id == company_id,
            TaskDependency.task_id == task.id,
            TaskDependency.depends_on_task_id == depends_on.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "This dependency already exists")

    # Would adding task -> depends_on create a cycle? That's true exactly when
    # depends_on already (transitively) depends on task.
    if _depends_transitively(db, company_id, depends_on.id, task.id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That would create a circular dependency")

    db.add(TaskDependency(company_id=company_id, task_id=task.id, depends_on_task_id=depends_on.id))
    db.commit()
    db.refresh(task)
    return task


def remove_dependency(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID, depends_on_task_id: uuid.UUID
) -> Task:
    task = get_task(db, company_id, project_id, task_id)
    link = (
        db.query(TaskDependency)
        .filter(
            TaskDependency.company_id == company_id,
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_task_id == depends_on_task_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dependency not found")
    db.delete(link)
    db.commit()
    db.refresh(task)
    return task
