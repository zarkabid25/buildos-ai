"""Supplier-portal notification feed (Phase 8) -- mirrors notification_service.py's
tenant pattern exactly, scoped by supplier_user_id instead of company_id+user_id
since SupplierUser has no company_id at all."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.platform_notification import SupplierNotification


def create_notification(db: Session, supplier_user_id: uuid.UUID, notification_type: str, title: str, body: str | None = None, link: str | None = None) -> SupplierNotification:
    notification = SupplierNotification(supplier_user_id=supplier_user_id, notification_type=notification_type, title=title, body=body, link=link)
    db.add(notification)
    return notification


def notify_members(db: Session, marketplace_supplier_id: uuid.UUID, notification_type: str, title: str, body: str | None = None, link: str | None = None) -> list[SupplierNotification]:
    from app.models.enums import SupplierMembershipStatus
    from app.models.supplier_user import SupplierMembership

    member_ids = [
        row[0] for row in db.query(SupplierMembership.supplier_user_id).filter(
            SupplierMembership.marketplace_supplier_id == marketplace_supplier_id, SupplierMembership.status == SupplierMembershipStatus.ACTIVE
        ).all()
    ]
    return [create_notification(db, uid, notification_type, title, body, link) for uid in member_ids]


def list_notifications(db: Session, supplier_user_id: uuid.UUID, unread_only: bool = False) -> list[SupplierNotification]:
    query = db.query(SupplierNotification).filter(SupplierNotification.supplier_user_id == supplier_user_id)
    if unread_only:
        query = query.filter(SupplierNotification.is_read.is_(False))
    return query.order_by(SupplierNotification.created_at.desc()).all()


def mark_read(db: Session, supplier_user_id: uuid.UUID, notification_id: uuid.UUID) -> SupplierNotification:
    notification = db.query(SupplierNotification).filter(SupplierNotification.id == notification_id, SupplierNotification.supplier_user_id == supplier_user_id).first()
    if not notification:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
