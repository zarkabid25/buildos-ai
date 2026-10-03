import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead


def record(
    db: Session,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    summary: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry to the caller's transaction. It's committed (or rolled
    back) together with the change it describes, so the log can't claim something
    happened that didn't, or miss something that did."""
    db.add(
        AuditLog(
            company_id=company_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:500],
            details=details,
        )
    )


def list_entries(
    db: Session, company_id: uuid.UUID, entity_type: str | None = None, limit: int = 100
) -> list[AuditLogRead]:
    query = (
        db.query(AuditLog, User.full_name)
        .outerjoin(User, (User.id == AuditLog.actor_id) & (User.company_id == company_id))
        .filter(AuditLog.company_id == company_id)
    )
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        AuditLogRead.model_validate(entry).model_copy(update={"actor_name": name}) for entry, name in rows
    ]
