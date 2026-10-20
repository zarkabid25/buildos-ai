"""Platform-admin AI features (Phase 9, PLAT-048): lead summaries, revenue
trend summaries, and supplier-matching explanations. Every endpoint fetches
real data through the existing, unmodified service/router functions first,
then asks the LLM to narrate it -- the model never queries anything itself
and is explicitly instructed not to invent figures (app/ai/narrate.py)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.llm import LLMClient, get_llm_dependency
from app.ai.narrate import generate_narration
from app.api.deps import get_current_platform_admin
from app.db.session import get_db
from app.models.platform_admin import PlatformAdmin
from app.schemas.ai import AiNarrationResponse
from app.services import crm_service, marketplace_integration_service

router = APIRouter(prefix="/platform/ai", tags=["platform-ai"])

SYSTEM_PROMPT = (
    "You are an assistant for BuildOS AI's platform staff, helping them work a CRM pipeline, "
    "read revenue trends, and understand supplier matches. You are advisory only: you never award "
    "anything, change a subscription, approve a payment, or adjust a commission -- a human does all "
    "of that separately."
)


@router.post("/crm-organizations/{org_id}/insights", response_model=AiNarrationResponse)
def crm_lead_insights(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
    llm: LLMClient = Depends(get_llm_dependency),
) -> AiNarrationResponse:
    """Lead summary + suggested follow-up actions, from this organization's
    real stage, notes, contacts and logged activities -- never from a
    separate, re-fetched or imagined dataset."""
    org = crm_service.get_organization(db, org_id)
    data = (
        f"Organization: {org.name}\nPipeline: {org.pipeline_type.value}\nStage: {org.stage.value}\n"
        f"Source: {org.source or 'unknown'}\nIndustry: {org.industry or 'unknown'}\nNotes: {org.notes or 'none'}\n"
        f"Contacts: {[(c.name, c.title, c.email) for c in org.contacts]}\n"
        f"Activities (most recent first): {[(a.type.value, a.summary, str(a.due_at), str(a.completed_at)) for a in org.activities]}"
    )
    text = generate_narration(
        llm, SYSTEM_PROMPT,
        f"Summarize this CRM lead for a staff member catching up on it, then suggest 2-4 concrete next follow-up actions "
        f"based only on its real stage and activity history below:\n\n{data}",
        actor_key=f"staff:{admin.id}", feature="crm_lead_insights",
    )
    return AiNarrationResponse(narration=text)


@router.get("/revenue-summary", response_model=AiNarrationResponse)
def revenue_trend_summary(
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
    llm: LLMClient = Depends(get_llm_dependency),
) -> AiNarrationResponse:
    """Reuses the real, already-computed SaaS billing and marketplace
    commission revenue dashboards -- never a separate calculation, so this
    can never disagree with the numbers staff see on those screens."""
    from app.api.v1.platform_billing import billing_revenue
    from app.api.v1.platform_commissions import revenue_dashboard

    billing = billing_revenue(db=db, _admin=admin)
    commissions = revenue_dashboard(db=db, _admin=admin)
    data = (
        f"SaaS subscription revenue: MRR={billing.mrr}, revenue_collected={billing.revenue_collected}, "
        f"outstanding={billing.outstanding_amount}, active_subscriptions={billing.active_subscriptions}, "
        f"trialing={billing.trialing_subscriptions}, monthly_trend={[(p.month, p.amount) for p in billing.monthly_trend]}, "
        f"plan_distribution={[(p.plan_name, p.count) for p in billing.plan_distribution]}\n"
        f"Marketplace commission revenue: earned={commissions.commission_earned}, invoiced={commissions.commission_invoiced}, "
        f"collected={commissions.commission_collected}, outstanding={commissions.outstanding_commission}, "
        f"attributed_order_count={commissions.marketplace_attributed_order_count}, "
        f"monthly_trend={[(p.month, p.amount) for p in commissions.monthly_trend]}, "
        f"top_suppliers={[(c.marketplace_supplier_name, c.commission_earned) for c in commissions.supplier_contributions[:5]]}"
    )
    text = generate_narration(
        llm, SYSTEM_PROMPT,
        f"Summarize the revenue trends below in a few sentences, calling out anything notable (growth, "
        f"concentration in one plan or supplier, a large outstanding balance). Keep SaaS subscription "
        f"revenue and marketplace commission revenue clearly distinct -- never add them together as one figure:\n\n{data}",
        actor_key=f"staff:{admin.id}", feature="revenue_trend_summary",
    )
    return AiNarrationResponse(narration=text)


@router.get("/marketplace/match-explanation", response_model=AiNarrationResponse)
def supplier_match_explanation(
    company_id: uuid.UUID,
    material_id: uuid.UUID,
    area: str | None = None,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
    llm: LLMClient = Depends(get_llm_dependency),
) -> AiNarrationResponse:
    """Explains the real, already-computed deterministic matches (PLAT-027)
    in plain language -- never invents a match, a price, or a score that
    isn't already in the real result set."""
    matches = marketplace_integration_service.find_eligible_suppliers(db, company_id, material_id, area)
    if not matches:
        return AiNarrationResponse(narration="No eligible suppliers were found for this material/area combination -- there's nothing to explain.")
    data = "\n".join(
        f"- {m.supplier_name}: product={m.product_name}, price={m.price}, moq={m.minimum_order_quantity}, "
        f"lead_time_days={m.lead_time_days}, coverage_areas={m.coverage_areas}, matched_via={m.matched_via}, verification={m.verification_status.value}"
        for m in matches
    )
    text = generate_narration(
        llm, SYSTEM_PROMPT,
        f"Explain in plain language why each of these real supplier matches was returned, and which looks strongest "
        f"on price/lead time/coverage -- using only the data below, never inventing a supplier or number not listed:\n\n{data}",
        actor_key=f"staff:{admin.id}", feature="supplier_match_explanation",
    )
    return AiNarrationResponse(narration=text)
