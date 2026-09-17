import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.project_member import ProjectMember
from app.models.user import User
from app.services.project_service import get_project


def list_members(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[ProjectMember]:
    get_project(db, company_id, project_id)  # ensures tenant ownership
    return (
        db.query(ProjectMember)
        .options(joinedload(ProjectMember.user))
        .filter(ProjectMember.project_id == project_id)
        .all()
    )


def add_member(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> ProjectMember:
    get_project(db, company_id, project_id)

    user = db.query(User).filter(User.id == user_id, User.company_id == company_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found in this company")

    existing = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a project member")

    member = ProjectMember(project_id=project_id, user_id=user_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, member_id: uuid.UUID
) -> None:
    get_project(db, company_id, project_id)

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.id == member_id, ProjectMember.project_id == project_id)
        .first()
    )
    if not member:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project member not found")

    db.delete(member)
    db.commit()
