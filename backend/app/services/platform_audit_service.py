import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.platform_admin import PlatformAdmin
from app.models.platform_audit import PlatformAuditLog
from app.schemas.platform import PlatformAuditEntry


def record(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    summary: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Added to the caller's transaction, committed together with the change it
    describes -- same discipline as the tenant audit_service."""
    db.add(
        PlatformAuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:500],
            details=details,
        )
    )


def list_entries(
    db: Session,
    limit: int = 100,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> list[PlatformAuditEntry]:
    query = db.query(PlatformAuditLog, PlatformAdmin.full_name).outerjoin(
        PlatformAdmin, PlatformAdmin.id == PlatformAuditLog.actor_id
    )
    if entity_type:
        query = query.filter(PlatformAuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(PlatformAuditLog.entity_id == entity_id)
    rows = query.order_by(PlatformAuditLog.created_at.desc()).limit(limit).all()
    return [
        PlatformAuditEntry(
            id=entry.id,
            created_at=entry.created_at,
            actor_id=entry.actor_id,
            actor_name=name,
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            summary=entry.summary,
            details=entry.details,
        )
        for entry, name in rows
    ]
