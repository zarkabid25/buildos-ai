"""Phase 9.1 (Task 4): centralized, concurrency-safe enforcement of
`SubscriptionPlan.ai_monthly_messages`. Every AI endpoint that costs the
platform real provider spend -- the Phase 9 narration endpoints
(app/ai/narrate.py) and the existing chat copilot (app/ai/copilot.py) --
must call `reserve_usage` before calling the LLM, never after: a quota
exists to cap spend, so it has to gate the call, not just count it
afterwards.

Why a real row instead of the existing in-memory `app/core/rate_limit.py`
limiter: that limiter is a flat per-actor rate (resets on process restart,
never shared without Redis, no concept of a calendar month or a plan's
`ai_monthly_messages`). This is the one place a company's actual billed
plan limit is enforced, and it has to survive restarts and be correct
under concurrent requests -- hence the atomic UPSERT below, not a
read-then-write.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.ai_usage import AiUsageCounter
from app.services import entitlement_service


def _current_period() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year:04d}-{now.month:02d}"


def current_usage(db: Session, company_id: uuid.UUID) -> int:
    row = db.execute(
        select(AiUsageCounter).where(AiUsageCounter.company_id == company_id, AiUsageCounter.period == _current_period())
    ).scalar_one_or_none()
    return row.message_count if row else 0


def _increment_atomically(db: Session, company_id: uuid.UUID) -> int:
    """A single atomic UPSERT (INSERT ... ON CONFLICT DO UPDATE ... RETURNING)
    so two concurrent requests for the same company in the same month can
    never both read "0, still under the limit" and both proceed -- each
    commit serializes through the database's own row-level locking on the
    unique (company_id, period) constraint, not application-level locking."""
    period = _current_period()
    if db.bind.dialect.name == "postgresql":
        stmt = (
            pg_insert(AiUsageCounter)
            .values(id=uuid.uuid4(), company_id=company_id, period=period, message_count=1)
            .on_conflict_do_update(
                index_elements=["company_id", "period"],
                set_={"message_count": AiUsageCounter.message_count + 1},
            )
            .returning(AiUsageCounter.message_count)
        )
        new_count = db.execute(stmt).scalar_one()
    else:
        # SQLite (tests only -- no production deployment target uses it):
        # no native UPSERT-with-increment in the ORM-portable form used
        # here, so this path relies on SQLite's own single-writer locking
        # rather than being proven safe under real concurrency. Fine for
        # tests; Postgres is the only concurrency-safe path and the only
        # one this system actually deploys on.
        row = db.execute(
            select(AiUsageCounter).where(AiUsageCounter.company_id == company_id, AiUsageCounter.period == period)
        ).scalar_one_or_none()
        if row is None:
            row = AiUsageCounter(company_id=company_id, period=period, message_count=0)
            db.add(row)
            db.flush()
        row.message_count += 1
        new_count = row.message_count
    db.commit()
    return new_count


def reserve_usage(db: Session, company_id: uuid.UUID) -> None:
    """Raises 429 if this would exceed the company's plan quota for the
    current month, otherwise atomically reserves one message and returns.
    No plan, no live subscription, or a plan with `ai_monthly_messages`
    unset all mean unlimited -- same "unrestricted until you actually have
    a limiting plan" rule entitlement_service already applies to project
    and team-member limits, kept consistent here rather than inventing a
    stricter default for AI specifically."""
    ent = entitlement_service.get_effective_entitlements(db, company_id)
    if ent.ai_monthly_messages is None:
        return
    # Reserve first (atomic), then check -- this still caps spend at
    # "limit + 1 request ever processed over, in the worst concurrent
    # case" rather than allowing unbounded overshoot, and never requires a
    # separate rollback step on the common path.
    new_count = _increment_atomically(db, company_id)
    if new_count > ent.ai_monthly_messages:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"This company has reached its plan's AI usage limit for this month ({ent.ai_monthly_messages} messages). Upgrade the plan for more.",
        )
