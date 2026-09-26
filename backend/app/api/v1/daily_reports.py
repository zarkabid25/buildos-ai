import uuid

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.daily_report import DailyReportCreate, DailyReportPhotoRead, DailyReportRead
from app.services import daily_report_service

router = APIRouter(tags=["daily-reports"])

CAN_WRITE = (
    UserRole.SUPER_ADMIN,
    UserRole.COMPANY_ADMIN,
    UserRole.PROJECT_MANAGER,
    UserRole.SITE_ENGINEER,
)


@router.get("/projects/{project_id}/daily-reports", response_model=list[DailyReportRead])
def list_reports(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DailyReportRead]:
    return daily_report_service.list_reports(db, current_user.company_id, project_id)


@router.post("/projects/{project_id}/daily-reports", response_model=DailyReportRead, status_code=201)
def create_report(
    project_id: uuid.UUID,
    payload: DailyReportCreate,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> DailyReportRead:
    return daily_report_service.create_report(
        db, current_user.company_id, current_user.id, project_id, payload
    )


@router.get("/daily-reports/{report_id}", response_model=DailyReportRead)
def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DailyReportRead:
    return daily_report_service.get_report(db, current_user.company_id, report_id)


@router.post("/daily-reports/{report_id}/photos", response_model=DailyReportPhotoRead, status_code=201)
async def upload_photo(
    report_id: uuid.UUID,
    file: UploadFile,
    current_user: User = Depends(require_roles(*CAN_WRITE)),
    db: Session = Depends(get_db),
) -> DailyReportPhotoRead:
    return await daily_report_service.add_photo(db, current_user.company_id, report_id, file)


@router.get("/daily-reports/{report_id}/photos/{photo_id}")
def download_photo(
    report_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    photo, path = daily_report_service.get_photo_file(db, current_user.company_id, report_id, photo_id)
    return FileResponse(path, media_type=photo.content_type, filename=photo.original_filename)
