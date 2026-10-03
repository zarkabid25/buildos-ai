import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.db.updates import apply_changes
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectHealth, ProjectSummary, ProjectUpdate

# A project is flagged "at risk" when it is active and the elapsed fraction of its
# schedule is more than 15 percentage points ahead of its reported progress. This is
# a placeholder heuristic ahead of the full risk engine (Epic 17 / BUILD-088).
SCHEDULE_RISK_THRESHOLD = 15


def get_schedule_variance_percent(project: Project, today: date) -> int | None:
    """Elapsed schedule % minus reported progress %. Positive means behind
    schedule (more time has elapsed than work reported done); negative means
    ahead. None if there isn't enough data (no dates, or not yet started)."""
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


def get_schedule_variance_days(project: Project, today: date) -> int | None:
    """The variance above, expressed in days of the project's own timeline
    rather than percentage points, so it reads as "6 days behind" not "8%"."""
    variance_percent = get_schedule_variance_percent(project, today)
    if variance_percent is None:
        return None
    total_days = (project.end_date - project.start_date).days
    return round(variance_percent / 100 * total_days)


def _is_at_risk(project: Project, today: date) -> bool:
    if project.status != ProjectStatus.ACTIVE:
        return False
    variance = get_schedule_variance_percent(project, today)
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


def _check_dates(project: Project) -> None:
    # Checked on the combined result, since an update may change only one of the two.
    if project.start_date and project.end_date and project.end_date < project.start_date:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "End date can't be before the start date")


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
    _check_dates(project)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(
    db: Session, company_id: uuid.UUID, project_id: uuid.UUID, payload: ProjectUpdate
) -> Project:
    project = get_project(db, company_id, project_id)
    apply_changes(project, payload.model_dump(exclude_unset=True))
    _check_dates(project)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> None:
    project = get_project(db, company_id, project_id)
    # Expenses, POs, stock allocations etc. are history; deleting the project would
    # orphan them (or, on Postgres, fail outright). Found from the schema itself so a
    # new table that references projects is covered automatically.
    in_use = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if any(fk.target_fullname == "projects.id" for fk in column.foreign_keys):
                if db.query(table).filter(column == project_id).first() is not None:
                    in_use.append(table.name.replace("_", " "))
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This project still has {', '.join(sorted(set(in_use)))}. Set its status to cancelled instead.",
        )
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
    # Imported here because both services import get_project from this module.
    from app.services import boq_service, finance_service

    project = get_project(db, company_id, project_id)
    basis: dict[str, str] = {}

    variance = get_schedule_variance_percent(project, date.today())
    schedule_score = None if variance is None else max(0, min(100, 100 - max(0, variance) * 2))
    if schedule_score is not None:
        basis["schedule"] = f"{max(0, variance)} points behind the elapsed schedule; 2 points lost per point behind."

    # Same gate as the cost insight: with 0% progress the forecast is only spend so far.
    cost_score = None
    budget = Decimal(str(project.budget))
    if project.progress_percent > 0 and budget > 0:
        cost = finance_service.get_project_cost_summary(db, company_id, project_id)
        overrun_percent = max(Decimal("0"), cost.expected_variance / budget * 100)
        cost_score = max(0, min(100, round(100 - overrun_percent * 2)))
        basis["cost"] = (
            f"Forecast {cost.forecast:.0f} against budget {budget:.0f} "
            f"({overrun_percent:.1f}% over); 2 points lost per 1% forecast overrun."
        )

    inventory_score = None
    tracked = [line for line in boq_service.get_boq_vs_actual(db, company_id, project_id).lines if line.status != "not_tracked"]
    if tracked:
        over = sum(1 for line in tracked if line.status == "over_plan")
        inventory_score = round((len(tracked) - over) / len(tracked) * 100)
        basis["inventory"] = f"{over} of {len(tracked)} material-linked BOQ lines have used more than planned."

    # Quality, safety, labor and procurement have no scoring data behind them
    # yet, so they stay null rather than showing invented numbers.
    available = [s for s in (schedule_score, cost_score, inventory_score) if s is not None]
    overall_score = round(sum(available) / len(available)) if available else None

    return ProjectHealth(
        overall_score=overall_score,
        schedule_score=schedule_score,
        cost_score=cost_score,
        inventory_score=inventory_score,
        quality_score=None,
        safety_score=None,
        labor_score=None,
        procurement_score=None,
        is_at_risk=_is_at_risk(project, date.today()),
        basis=basis,
    )
