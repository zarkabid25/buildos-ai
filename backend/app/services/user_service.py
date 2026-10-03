import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.updates import apply_changes
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import PasswordChange, UserAdminUpdate, UserSelfUpdate
from app.services import audit_service


def update_me(db: Session, user: User, payload: UserSelfUpdate) -> User:
    user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: PasswordChange) -> None:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()


def list_users(db: Session, company_id: uuid.UUID) -> list[User]:
    return db.query(User).filter(User.company_id == company_id).order_by(User.full_name.asc()).all()


def update_user(db: Session, actor: User, user_id: uuid.UUID, payload: UserAdminUpdate) -> User:
    user = db.query(User).filter(User.company_id == actor.company_id, User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    changes = payload.model_dump(exclude_unset=True)
    # An admin changing their own role or deactivating themselves could leave the
    # company with nobody able to manage it.
    if user.id == actor.id and changes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can't change your own role or status")
    # Only a super admin may create or modify another super admin.
    touches_super = user.role == UserRole.SUPER_ADMIN or changes.get("role") == UserRole.SUPER_ADMIN
    if touches_super and actor.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a super admin can manage super admins")

    before = {"role": user.role, "is_active": user.is_active}
    apply_changes(user, changes)
    if "role" in changes and changes["role"] != before["role"]:
        audit_service.record(
            db, actor.company_id, actor.id, "user.role_changed", "user", user.id,
            f"{user.full_name}: role {before['role'].value} -> {user.role.value}",
            {"from": before["role"].value, "to": user.role.value},
        )
    if "is_active" in changes and changes["is_active"] != before["is_active"]:
        action = "user.reactivated" if user.is_active else "user.deactivated"
        audit_service.record(
            db, actor.company_id, actor.id, action, "user", user.id,
            f"{user.full_name} {'reactivated' if user.is_active else 'deactivated'}",
        )
    db.commit()
    db.refresh(user)
    return user
