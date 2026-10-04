import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserUpdateRole(BaseModel):
    role: UserRole


class UserSelfUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserAdminUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class InvitationCreate(BaseModel):
    email: EmailStr
    role: UserRole
    full_name: str | None = Field(default=None, max_length=255)


class InvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    invited_by_name: str | None
    created_at: datetime
    expires_at: datetime
    expired: bool


class InvitationCreated(InvitationRead):
    # Shown once: only a hash is stored, so the link can't be shown again later.
    token: str


class InvitationInfo(BaseModel):
    """What the person opening an invite link sees before accepting (public)."""

    company_name: str
    email: str
    full_name: str | None
    role: UserRole


class AcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)
