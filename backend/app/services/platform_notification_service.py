"""Platform-staff notification feed (Phase 8) -- a shared feed, not
per-staff read state, same simplification already implicit in
PlatformAuditLog being global rather than per-viewer. Used for demo
requests, supplier applications and new support tickets so staff don't have
to go looking for them."""

import uuid

from sqlalchemy.orm import Session

from app.models.platform_notification import PlatformNotification


def notify_staff(db: Session, notification_type: str, title: str, body: str | None = None, link: str | None = None) -> PlatformNotification:
    notification = PlatformNotification(notification_type=notification_type, title=title, body=body, link=link)
    db.add(notification)
    return notification


def list_notifications(db: Session, include_dismissed: bool = False) -> list[PlatformNotification]:
    query = db.query(PlatformNotification)
    if not include_dismissed:
        query = query.filter(PlatformNotification.dismissed_at.is_(None))
    return query.order_by(PlatformNotification.created_at.desc()).all()


def dismiss(db: Session, notification_id: uuid.UUID) -> None:
    from datetime import datetime, timezone

    notification = db.query(PlatformNotification).filter(PlatformNotification.id == notification_id).first()
    if notification:
        notification.dismissed_at = datetime.now(timezone.utc)
        db.commit()
