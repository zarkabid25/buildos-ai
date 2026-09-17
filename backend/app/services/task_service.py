import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.project_service import get_project


def list_tasks(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[Task]:
    get_project(db, company_id, project_id)
    return (
        db.query(Task)
        .filter(Task.company_id == company_id, Task.project_id == project_id)
        .order_by(Task.created_at.desc())
        .all()
    )


def create_task(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, payload: TaskCreate
) -> Task:
    get_project(db, company_id, project_id)
    task = Task(company_id=company_id, project_id=project_id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID, payload: TaskUpdate
) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id, Task.company_id == company_id)
        .first()
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, company_id: uuid.UUID, project_id: uuid.UUID, task_id: uuid.UUID) -> None:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.project_id == project_id, Task.company_id == company_id)
        .first()
    )
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    db.delete(task)
    db.commit()
