import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.milestone import Milestone
from app.schemas.task import ProjectSchedule, ScheduleMilestone, TaskRead
from app.services import project_service, task_service


def get_project_schedule(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> ProjectSchedule:
    project = project_service.get_project(db, company_id, project_id)
    tasks = task_service.list_tasks(db, company_id, project_id)
    milestones = (
        db.query(Milestone)
        .filter(Milestone.company_id == company_id, Milestone.project_id == project_id)
        .order_by(Milestone.due_date.asc().nulls_last())
        .all()
    )

    today = date.today()
    variance_percent = project_service.get_schedule_variance_percent(project, today)
    variance_days = project_service.get_schedule_variance_days(project, today)

    if variance_percent is None:
        note = "Set both a start and end date on the project to see schedule variance."
    elif variance_percent > 0:
        note = f"{variance_days} day(s) behind schedule at the current progress rate."
    elif variance_percent < 0:
        note = f"{abs(variance_days)} day(s) ahead of schedule at the current progress rate."
    else:
        note = "Exactly on schedule."

    return ProjectSchedule(
        tasks=[TaskRead.model_validate(t) for t in tasks],
        milestones=[ScheduleMilestone.model_validate(m) for m in milestones],
        schedule_variance_percent=variance_percent,
        schedule_variance_days=variance_days,
        variance_note=note,
    )
