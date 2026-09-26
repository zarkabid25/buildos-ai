import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.storage import IMAGE_TYPES, resolve_path, save_upload
from app.models.daily_report import DailyReport, DailyReportPhoto
from app.schemas.daily_report import DailyReportCreate
from app.services.project_service import get_project


def list_reports(db: Session, company_id: uuid.UUID, project_id: uuid.UUID) -> list[DailyReport]:
    get_project(db, company_id, project_id)
    return (
        db.query(DailyReport)
        .options(joinedload(DailyReport.photos))
        .filter(DailyReport.company_id == company_id, DailyReport.project_id == project_id)
        .order_by(DailyReport.report_date.desc())
        .all()
    )


def get_report(db: Session, company_id: uuid.UUID, report_id: uuid.UUID) -> DailyReport:
    report = (
        db.query(DailyReport)
        .options(joinedload(DailyReport.photos))
        .filter(DailyReport.company_id == company_id, DailyReport.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Daily report not found")
    return report


def create_report(
    db: Session,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: DailyReportCreate,
) -> DailyReport:
    get_project(db, company_id, project_id)

    existing = (
        db.query(DailyReport)
        .filter(DailyReport.project_id == project_id, DailyReport.report_date == payload.report_date)
        .first()
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "A daily report already exists for this project and date")

    report = DailyReport(
        company_id=company_id, project_id=project_id, created_by_id=user_id, **payload.model_dump()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


async def add_photo(
    db: Session, company_id: uuid.UUID, report_id: uuid.UUID, file: UploadFile
) -> DailyReportPhoto:
    report = get_report(db, company_id, report_id)
    key, size = await save_upload(file, company_id, f"daily-reports/{report.id}", IMAGE_TYPES)

    photo = DailyReportPhoto(
        company_id=company_id,
        daily_report_id=report.id,
        storage_key=key,
        original_filename=(file.filename or "photo")[:255],
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return photo


def get_photo_file(db: Session, company_id: uuid.UUID, report_id: uuid.UUID, photo_id: uuid.UUID):
    photo = (
        db.query(DailyReportPhoto)
        .filter(
            DailyReportPhoto.id == photo_id,
            DailyReportPhoto.daily_report_id == report_id,
            DailyReportPhoto.company_id == company_id,
        )
        .first()
    )
    if not photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Photo not found")
    return photo, resolve_path(photo.storage_key)
