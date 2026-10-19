"""Effective entitlements and usage enforcement (PLAT-031/032). One function,
get_effective_entitlements, is the single source of truth three different
things read from: the company's own "Usage and plan limits" screen, the
guard calls added to project/invitation creation, and the marketplace
feature-flag check -- so they can never disagree with each other."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.billing import CompanyLegacyEntitlement, CompanySubscription, SubscriptionPlan
from app.models.enums import LIVE_SUBSCRIPTION_STATUSES, SubscriptionStatus
from app.models.project import Project
from app.models.user import User
from app.schemas.billing import EntitlementRead


def get_legacy_entitlement(db: Session, company_id: uuid.UUID) -> CompanyLegacyEntitlement | None:
    return (
        db.query(CompanyLegacyEntitlement)
        .filter(CompanyLegacyEntitlement.company_id == company_id, CompanyLegacyEntitlement.revoked_at.is_(None))
        .first()
    )


def get_effective_entitlements(db: Session, company_id: uuid.UUID) -> EntitlementRead:
    sub = (
        db.query(CompanySubscription)
        .filter(CompanySubscription.company_id == company_id, CompanySubscription.status.in_(LIVE_SUBSCRIPTION_STATUSES))
        .first()
    )
    current_projects = db.query(Project).filter(Project.company_id == company_id).count()
    current_team_members = db.query(User).filter(User.company_id == company_id).count()

    if sub:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == sub.plan_id).first()
        return EntitlementRead(
            source="subscription",
            plan_name=plan.name,
            max_projects=plan.max_projects,
            max_team_members=plan.max_team_members,
            ai_monthly_messages=plan.ai_monthly_messages,
            storage_gb=plan.storage_gb,
            marketplace_included=plan.marketplace_included,
            current_projects=current_projects,
            current_team_members=current_team_members,
            billing_status=sub.status,
            current_period_end=sub.current_period_end,
            grace_period_ends_at=sub.grace_period_ends_at,
        )

    legacy = get_legacy_entitlement(db, company_id)
    if legacy:
        # Grandfathered (PLAT-032): unrestricted, exactly as before Phase 5 --
        # never auto-charged, never newly limited.
        return EntitlementRead(
            source="legacy", plan_name=None, max_projects=None, max_team_members=None, ai_monthly_messages=None,
            storage_gb=None, marketplace_included=True, current_projects=current_projects, current_team_members=current_team_members,
            billing_status=None, current_period_end=None, grace_period_ends_at=None,
        )

    # A company with neither a live subscription nor a legacy grant -- this is
    # NOT a reason to block it. Phase 5 adds subscriptions as an available
    # mechanism; it does not retroactively require one to keep using the app
    # existing companies could use freely before. Enforcement only has real
    # teeth once a company actually has a live subscription with real limits
    # (source == "subscription"); until/unless this company chooses to
    # subscribe, it behaves exactly as it always did -- unrestricted, same as
    # "legacy". This is what keeps the existing /auth/register -> use-the-app
    # flow (and the whole pre-Phase-5 test suite) working unchanged.
    return EntitlementRead(
        source="none", plan_name=None, max_projects=None, max_team_members=None, ai_monthly_messages=None, storage_gb=None,
        marketplace_included=False, current_projects=current_projects, current_team_members=current_team_members,
        billing_status=None, current_period_end=None, grace_period_ends_at=None,
    )


def enforce_project_limit(db: Session, company_id: uuid.UUID) -> None:
    ent = get_effective_entitlements(db, company_id)
    if ent.max_projects is not None and ent.current_projects >= ent.max_projects:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Plan limit reached: {ent.max_projects} project(s). Upgrade your plan to add more.")


def enforce_team_member_limit(db: Session, company_id: uuid.UUID) -> None:
    ent = get_effective_entitlements(db, company_id)
    if ent.max_team_members is not None and ent.current_team_members >= ent.max_team_members:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Plan limit reached: {ent.max_team_members} team member(s). Upgrade your plan to add more.")


def effective_marketplace_enabled(db: Session, company_id: uuid.UUID, operational_flag: bool) -> bool:
    """Combines the operational on/off switch (companies.marketplace_enabled,
    Day 33 -- never removed, always the first gate) with the subscription
    entitlement. The plan's marketplace_included only ever *restricts*
    something that would otherwise be allowed, and only once a company has
    actually chosen a real subscription -- a legacy company, or one that
    simply hasn't subscribed to anything yet, depends on nothing but the
    operational flag, exactly as it did before Phase 5 (Day 33) existed."""
    if not operational_flag:
        return False
    ent = get_effective_entitlements(db, company_id)
    if ent.source == "subscription":
        return ent.marketplace_included
    return True
