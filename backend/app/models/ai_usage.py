"""Phase 9.1 (Task 4): a durable, per-company monthly counter for AI usage,
enforcing `SubscriptionPlan.ai_monthly_messages` -- previously just a
displayed figure (see docs/RELEASE_READINESS.md's Phase 9 note). One row
per (company, calendar month); `period` is "YYYY-MM" so the natural sort
order is also chronological."""

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import TenantBase


class AiUsageCounter(TenantBase):
    __tablename__ = "ai_usage_counters"
    __table_args__ = (
        UniqueConstraint("company_id", "period", name="uq_ai_usage_counters_company_period"),
        Index("ix_ai_usage_counters_company_period", "company_id", "period"),
    )

    period: Mapped[str] = mapped_column(String(7), nullable=False)  # "YYYY-MM"
    message_count: Mapped[int] = mapped_column(nullable=False, default=0)
