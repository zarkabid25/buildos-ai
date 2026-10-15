import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import CrmActivityType, CrmPipelineType, CrmStage


class CrmContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    is_primary: bool = False


class CrmContactRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    title: str | None
    email: str | None
    phone: str | None
    is_primary: bool

    model_config = {"from_attributes": True}


class CrmActivityCreate(BaseModel):
    type: CrmActivityType
    summary: str = Field(min_length=1, max_length=500)
    due_at: datetime | None = None


class CrmActivityRead(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    type: CrmActivityType
    summary: str
    due_at: datetime | None
    completed_at: datetime | None
    created_by_id: uuid.UUID
    created_by_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrmOrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    pipeline_type: CrmPipelineType
    source: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = None
    owner_staff_id: uuid.UUID | None = None


class CrmOrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    stage: CrmStage | None = None
    source: str | None = Field(default=None, max_length=100)
    industry: str | None = Field(default=None, max_length=100)
    website: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    notes: str | None = None
    owner_staff_id: uuid.UUID | None = None


class CrmOrganizationRead(BaseModel):
    id: uuid.UUID
    name: str
    pipeline_type: CrmPipelineType
    stage: CrmStage
    source: str | None
    industry: str | None
    website: str | None
    phone: str | None
    email: str | None
    notes: str | None
    owner_staff_id: uuid.UUID | None
    owner_staff_name: str | None = None
    converted_company_id: uuid.UUID | None
    converted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrmOrganizationDetail(CrmOrganizationRead):
    contacts: list[CrmContactRead]
    activities: list[CrmActivityRead]


class CrmConvertRequest(BaseModel):
    """Exactly one of the two must be given. link_existing_company_id confirms an
    authorized match to a company that already exists (e.g. self-registered
    before the CRM record caught up); create_company starts a brand new one."""

    link_existing_company_id: uuid.UUID | None = None
    create_company_name: str | None = Field(default=None, min_length=2, max_length=255)
    create_company_code: str | None = Field(default=None, min_length=2, max_length=50)


class CrmConvertResult(BaseModel):
    organization: CrmOrganizationRead
    company_id: uuid.UUID
    already_converted: bool
