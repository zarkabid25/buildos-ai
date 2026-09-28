import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationRead, UnreadCount
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationRead]:
    return notification_service.list_notifications(db, current_user.company_id, current_user.id, unread_only)


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UnreadCount:
    return UnreadCount(unread_count=notification_service.get_unread_count(db, current_user.company_id, current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    return notification_service.mark_read(db, current_user.company_id, current_user.id, notification_id)


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UnreadCount:
    notification_service.mark_all_read(db, current_user.company_id, current_user.id)
    return UnreadCount(unread_count=0)
