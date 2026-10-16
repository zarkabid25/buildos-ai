import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import CompanyOnboardingStatus, PlatformStaffRole
from app.schemas.auth import TokenPair


class PlatformLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PlatformRefreshRequest(BaseModel):
    refresh_token: str


class PlatformAdminRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: PlatformStaffRole
    is_active: bool

    model_config = {"from_attributes": True}


class PlatformAuthResponse(TokenPair):
    admin: PlatformAdminRead


class PlatformStaffUpdate(BaseModel):
    role: PlatformStaffRole | None = None
    is_active: bool | None = None


class PlatformCompanyRead(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    currency: str
    email: str | None
    phone: str | None
    is_active: bool
    suspended_at: datetime | None
    onboarding_status: CompanyOnboardingStatus
    marketplace_enabled: bool
    created_at: datetime
    user_count: int

    model_config = {"from_attributes": True}


class PlatformCompanyList(BaseModel):
    total: int
    companies: list[PlatformCompanyRead]


class MarketplaceFlagUpdate(BaseModel):
    enabled: bool


class PlatformDashboard(BaseModel):
    active_companies: int
    suspended_companies: int
    pending_approval_companies: int
    total_users: int
    companies_created_last_30_days: int
    # Not yet real: no CRM, subscriptions, marketplace or commissions exist yet.
    monthly_recurring_revenue: float | None = Field(
        default=None, description="null until subscriptions/billing (Epic 27b) exist"
    )
    new_leads: int | None = Field(default=None, description="null until CRM (Epic 27b) exists")
    pending_supplier_verifications: int | None = Field(
        default=None, description="null until the supplier marketplace exists"
    )


class PlatformInvitationCreate(BaseModel):
    email: EmailStr
    role: PlatformStaffRole
    full_name: str | None = Field(default=None, max_length=255)


class PlatformInvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: PlatformStaffRole
    invited_by_name: str | None
    created_at: datetime
    expires_at: datetime
    expired: bool


class PlatformInvitationCreated(PlatformInvitationRead):
    token: str


class PlatformInvitationInfo(BaseModel):
    email: str
    full_name: str | None
    role: PlatformStaffRole


class PlatformAcceptInvitation(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PlatformAuditEntry(BaseModel):
    id: uuid.UUID
    created_at: datetime
    actor_id: uuid.UUID
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    summary: str
    details: dict[str, Any] | None
