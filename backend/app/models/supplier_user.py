"""Supplier self-service portal accounts (Phase 7, PLAT-038). A SupplierUser
is a login identity only -- which supplier organization(s) it may act for is
entirely decided by SupplierMembership rows, never by any field on
SupplierUser itself. This mirrors the existing separation in this app: a
tenant User is scoped by company_id, a PlatformAdmin by nothing (global
staff), and now a SupplierUser is scoped by its memberships -- explicitly,
never implicitly via company_id or any other borrowed identifier."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from app.db.base_class import TimestampedBase
from app.models.enums import SupplierMembershipRole, SupplierMembershipStatus


class SupplierUser(TimestampedBase):
    __tablename__ = "supplier_users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class SupplierMembership(TimestampedBase):
    """One supplier user's authorization to act for one marketplace supplier
    (PLAT-038). A user may hold multiple memberships (multiple suppliers); a
    supplier may have multiple members. Suspending or revoking is a status
    change here, never a deletion -- the membership's own history (who was
    ever authorized, and when that changed) stays intact."""

    __tablename__ = "supplier_memberships"
    __table_args__ = (UniqueConstraint("supplier_user_id", "marketplace_supplier_id", name="uq_supplier_membership"),)

    supplier_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_users.id"), index=True, nullable=False)
    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    role: Mapped[SupplierMembershipRole] = mapped_column(
        Enum(SupplierMembershipRole, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    status: Mapped[SupplierMembershipStatus] = mapped_column(
        Enum(SupplierMembershipStatus, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]),
        default=SupplierMembershipStatus.ACTIVE, index=True, nullable=False,
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SupplierInvitation(TimestampedBase):
    """Mirrors the existing tenant Invitation / PlatformInvitation models
    byte-for-byte (same token_hash + 7-day-expiry mechanics in
    supplier_invitation_service.py) -- a SupplierUser is only ever created by
    accepting one of these, never by open self-registration, and it must
    always name a real, already-approved marketplace supplier (never creates
    one)."""

    __tablename__ = "supplier_invitations"

    marketplace_supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("marketplace_suppliers.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[SupplierMembershipRole] = mapped_column(
        Enum(SupplierMembershipRole, native_enum=False, length=20, values_callable=lambda e: [x.value for x in e]), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Exactly one of these two is set -- platform staff onboarding a
    # supplier's first user, or an existing OWNER/ADMIN inviting a teammate.
    invited_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
    invited_by_supplier_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("supplier_users.id"), nullable=True)
