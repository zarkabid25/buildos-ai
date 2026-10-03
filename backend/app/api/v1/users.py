import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserAdminUpdate, UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

CAN_MANAGE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_roles(*CAN_MANAGE)), db: Session = Depends(get_db)
) -> list[UserRead]:
    return user_service.list_users(db, current_user.company_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> UserRead:
    return user_service.update_user(db, current_user, user_id, payload)
