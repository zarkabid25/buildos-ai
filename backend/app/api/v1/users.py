import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import InvitationCreate, InvitationCreated, InvitationRead, UserAdminUpdate, UserRead
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

CAN_MANAGE = (UserRole.SUPER_ADMIN, UserRole.COMPANY_ADMIN)


@router.get("", response_model=list[UserRead])
def list_users(
    current_user: User = Depends(require_roles(*CAN_MANAGE)), db: Session = Depends(get_db)
) -> list[UserRead]:
    return user_service.list_users(db, current_user.company_id)


@router.get("/invitations", response_model=list[InvitationRead])
def list_invitations(
    current_user: User = Depends(require_roles(*CAN_MANAGE)), db: Session = Depends(get_db)
) -> list[InvitationRead]:
    return user_service.list_invitations(db, current_user.company_id)


@router.post("/invitations", response_model=InvitationCreated, status_code=201)
def create_invitation(
    payload: InvitationCreate,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> InvitationCreated:
    return user_service.create_invitation(db, current_user, payload)


@router.delete("/invitations/{invitation_id}", status_code=204)
def revoke_invitation(
    invitation_id: uuid.UUID,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    user_service.revoke_invitation(db, current_user, invitation_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: uuid.UUID,
    payload: UserAdminUpdate,
    current_user: User = Depends(require_roles(*CAN_MANAGE)),
    db: Session = Depends(get_db),
) -> UserRead:
    return user_service.update_user(db, current_user, user_id, payload)
