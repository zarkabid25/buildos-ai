import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import ProjectStatus
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectHealth, ProjectSummary, ProjectUpdate

# A project is flagged "at risk" when it is active and the elapsed fraction of its
# schedule is more than 15 percentage points ahead of its reported progress. This is
# a placeholder heuristic ahead of the full risk engine (Epic 17 / BUILD-088).
SCHEDULE_RISK_THRESHOLD = 15


def _schedule_variance_percent(project: Project, today: date) -> int | None:
    """Elapsed schedule % minus reported progress %. None if there isn't enough
    data (no dates, or not yet started) to compute a variance."""
    if not project.start_date or not project.end_date:
        return None
    total_days = (project.end_date - project.start_date).days
    if total_days <= 0:
        return None
    elapsed_days = (today - project.start_date).days
    if elapsed_days < 0:
        return None
    elapsed_percent = max(0, min(100, round(elapsed_days / total_days * 100)))
    return elapsed_percent - project.progress_percent


def _is_at_risk(project: Project, today: date) -> bool:
    if project.status != ProjectStatus.ACTIVE:
        return False
    variance = _schedule_variance_percent(project, today)
    return variance is not None and variance > SCHEDULE_RISK_THRESHOLD


def list_projects(db: Session, company_id: uuid.UUID) -> list[Project]:
    return (
        db.query(Project)
        .filter(Project.company_id == company_id)
        .order_by(Project.created_at.desc())
        .all()
    )


def get_project(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = (
        db.query(Project)
        .filter(Project.company_id == company_id, Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


def create_project(
    db: Session, company_id: uuid.UUID, created_by_id: uuid.UUID, payload: ProjectCreate
) -> Project:
    exists = (
        db.query(Project)
        .filter(Project.company_id == company_id, Project.code == payload.code)
        .first()
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Project code already in use")

    project = Project(
        company_id=company_id,
        created_by_id=created_by_id,
        **payload.model_dump(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, payload: ProjectUpdate
) -> Project:
    project = get_project(db, company_id, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> None:
    project = get_project(db, company_id, project_id)
    db.delete(project)
    db.commit()


def get_summary(db: Session, company_id: uuid.UUID) -> ProjectSummary:
    projects = list_projects(db, company_id)
    total_projects = len(projects)
    total_budget = sum((p.budget for p in projects), Decimal("0"))
    avg_progress = (
        sum(p.progress_percent for p in projects) / total_projects if total_projects else 0.0
    )
    today = date.today()
    at_risk_count = sum(1 for p in projects if _is_at_risk(p, today))

    return ProjectSummary(
        total_projects=total_projects,
        total_budget=total_budget,
        avg_progress=round(avg_progress, 1),
        at_risk_count=at_risk_count,
    )


def get_health(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> ProjectHealth:
    project = get_project(db, company_id, project_id)
    variance = _schedule_variance_percent(project, date.today())

    schedule_score = None if variance is None else max(0, min(100, 100 - max(0, variance) * 2))

    # Cost, inventory, quality, safety, labor and procurement scores depend on
    # modules not built yet (expenses, inventory, daily reports...). Reporting
    # fabricated numbers here would violate the "no invented data" rule, so they
    # stay null until their source data exists.
    return ProjectHealth(
        overall_score=schedule_score,
        schedule_score=schedule_score,
        cost_score=None,
        inventory_score=None,
        quality_score=None,
        safety_score=None,
        labor_score=None,
        procurement_score=None,
        is_at_risk=_is_at_risk(project, date.today()),
    )
