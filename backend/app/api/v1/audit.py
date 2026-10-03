from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.services import audit_service

router = APIRouter(prefix="/audit-log", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_log(
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)),
    db: Session = Depends(get_db),
) -> list[AuditLogRead]:
    return audit_service.list_entries(db, current_user.company_id, entity_type, limit)
