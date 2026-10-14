import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

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
    is_active: bool

    model_config = {"from_attributes": True}


class PlatformAuthResponse(TokenPair):
    admin: PlatformAdminRead


class PlatformCompanyRead(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    currency: str
    email: str | None
    phone: str | None
    is_active: bool
    suspended_at: datetime | None
    created_at: datetime
    user_count: int

    model_config = {"from_attributes": True}


class PlatformCompanyList(BaseModel):
    total: int
    companies: list[PlatformCompanyRead]


class PlatformDashboard(BaseModel):
    active_companies: int
    suspended_companies: int
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
