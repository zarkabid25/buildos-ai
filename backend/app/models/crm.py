import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import TimestampedBase
from app.models.enums import CrmActivityType, CrmPipelineType, CrmStage


class CrmOrganization(TimestampedBase):
    """A prospect BuildOS is selling to -- either a construction company (SaaS
    sales pipeline) or a supplier being recruited for the marketplace (supplier
    acquisition pipeline). Deliberately separate from Company: a CrmOrganization
    is not a tenant and has no login, until it's converted (PLAT-015)."""

    __tablename__ = "crm_organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pipeline_type: Mapped[CrmPipelineType] = mapped_column(
        Enum(CrmPipelineType, native_enum=False, length=30, values_callable=lambda e: [x.value for x in e]),
        index=True,
        nullable=False,
    )
    stage: Mapped[CrmStage] = mapped_column(
        Enum(CrmStage, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=CrmStage.NEW,
        index=True,
        nullable=False,
    )
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True
    )
    # Set once, at conversion (PLAT-015). Never reused by another organization --
    # enforced in the service layer, not a DB constraint, so a re-conversion
    # attempt can be detected and answered idempotently instead of failing.
    converted_company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    contacts: Mapped[list["CrmContact"]] = relationship(cascade="all, delete-orphan", order_by="CrmContact.created_at")
    activities: Mapped[list["CrmActivity"]] = relationship(
        cascade="all, delete-orphan", order_by="CrmActivity.created_at.desc()"
    )


class CrmContact(TimestampedBase):
    __tablename__ = "crm_contacts"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm_organizations.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)


class CrmActivity(TimestampedBase):
    """Calls, meetings, notes, and follow-up reminders (a TASK with a due_at)."""

    __tablename__ = "crm_activities"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crm_organizations.id"), index=True, nullable=False
    )
    type: Mapped[CrmActivityType] = mapped_column(
        Enum(CrmActivityType, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=False)
