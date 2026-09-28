import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.enums import NotificationType, UserRole
from app.models.notification import Notification
from app.models.user import User


def create_notification(
    db: Session,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> Notification:
    notification = Notification(
        company_id=company_id,
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        link=link,
    )
    db.add(notification)
    return notification


def notify_users_with_roles(
    db: Session,
    company_id: uuid.UUID,
    roles: tuple[UserRole, ...],
    notification_type: NotificationType,
    title: str,
    body: str | None = None,
    link: str | None = None,
    exclude_user_id: uuid.UUID | None = None,
) -> list[Notification]:
    """Fan out one notification per matching, active user. The caller who
    triggered the event (exclude_user_id) doesn't need to be told about their
    own action."""
    query = db.query(User).filter(
        User.company_id == company_id, User.role.in_(roles), User.is_active.is_(True)
    )
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)

    created = [
        create_notification(db, company_id, user.id, notification_type, title, body, link)
        for user in query.all()
    ]
    return created


def list_notifications(
    db: Session, company_id: uuid.UUID, user_id: uuid.UUID, unread_only: bool = False
) -> list[Notification]:
    query = db.query(Notification).filter(
        Notification.company_id == company_id, Notification.user_id == user_id
    )
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).all()


def get_unread_count(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.company_id == company_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .count()
    )


def _get_own_notification(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.company_id == company_id,
            Notification.user_id == user_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    return notification


def mark_read(db: Session, company_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification:
    notification = _get_own_notification(db, company_id, user_id, notification_id)
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, company_id: uuid.UUID, user_id: uuid.UUID) -> int:
    updated = (
        db.query(Notification)
        .filter(
            Notification.company_id == company_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .update({"is_read": True})
    )
    db.commit()
    return updated
