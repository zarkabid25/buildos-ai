"""Phase 9 AI business intelligence (PLAT-048): the single-shot narration
endpoints across all three portals. Scripts a fake model (same pattern as
test_ai_copilot_http.py) to exercise *our* code -- data isolation, graceful
degradation, and usage limiting -- not the real model's behavior."""

from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.ai.llm import get_llm_dependency
from app.main import app
from tests.test_marketplace_integration_http import enable_marketplace, make, make_verified_supplier, owner_headers
from tests.test_supplier_portal_http import onboarded_supplier


def text(t):
    return SimpleNamespace(type="text", text=t)


def reply(*blocks, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=list(blocks))


class FakeLLM:
    def __init__(self, response=None, raises=None):
        self.response = response
        self.raises = raises
        self.calls = []

    def create_message(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        if self.raises:
            raise self.raises
        return self.response


@pytest.fixture
def use_llm():
    def _use(fake):
        app.dependency_overrides[get_llm_dependency] = lambda: fake
        return fake

    yield _use
    app.dependency_overrides.pop(get_llm_dependency, None)


def _invited_rfq(client, auth, staff, mkt_supplier):
    company_id = enable_marketplace(client, staff, auth)
    project = make(client, auth, "/projects", {"name": "AI Tower", "code": "AITW", "budget": "1"})
    material = make(client, auth, "/materials", {"name": "AI Cement", "sku": "AICEM", "unit": "Bag"})
    res = client.post(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/connect", json={"create_new_erp_supplier": True}, headers=auth)
    assert res.status_code == 201, res.text
    rfq = make(client, auth, "/rfqs", {"title": "AI Cement RFQ", "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "50"}]})
    res = client.post(f"/api/v1/marketplace/rfqs/{rfq['id']}/invite-suppliers", json={"marketplace_supplier_ids": [mkt_supplier["id"]]}, headers=auth)
    assert res.status_code == 201, res.text
    return company_id, rfq


# ---- Company portal ---------------------------------------------------------------------------


def test_rfq_ai_summary_uses_only_real_data(client, auth_a, use_llm):
    staff = owner_headers(client, email="ai-staff1@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI Summary Co")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    fake = use_llm(FakeLLM(response=reply(text("This RFQ asks for 50 bags of AI Cement."))))
    res = client.get(f"/api/v1/rfqs/{rfq['id']}/ai/summary", headers=auth_a)
    assert res.status_code == 200, res.text
    assert "AI Cement" in res.json()["narration"]
    assert "AI Cement RFQ" in fake.calls[0]["messages"][0]["content"]  # the real RFQ data was actually sent


def test_rfq_ai_summary_cannot_see_another_companys_rfq(client, auth_a, auth_b, use_llm):
    staff = owner_headers(client, email="ai-staff2@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI Isolation Co")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    use_llm(FakeLLM(response=reply(text("summary"))))
    res = client.get(f"/api/v1/rfqs/{rfq['id']}/ai/summary", headers=auth_b)
    assert res.status_code == 404  # company B can't even reach company A's RFQ to summarize it


def test_ai_degrades_gracefully_when_not_configured(client, auth_a):
    """No dependency override at all -- exercises the real get_llm_dependency,
    which raises AINotConfigured since no LLM_API_KEY is set in tests."""
    staff = owner_headers(client, email="ai-staff3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI Unconfigured Co")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    res = client.get(f"/api/v1/rfqs/{rfq['id']}/ai/summary", headers=auth_a)
    assert res.status_code == 503
    assert "LLM_API_KEY" in res.json()["detail"]


def test_ai_handles_provider_rate_limit_gracefully(client, auth_a, use_llm):
    staff = owner_headers(client, email="ai-staff4@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI RateLimit Co")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    fake_response = httpx2.Response(429, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    use_llm(FakeLLM(raises=anthropic.RateLimitError("rate limited", response=fake_response, body=None)))
    res = client.get(f"/api/v1/rfqs/{rfq['id']}/ai/summary", headers=auth_a)
    assert res.status_code == 429


def test_supplier_recommendation_never_invents_a_price(client, auth_a, use_llm):
    staff = owner_headers(client, email="ai-staff5@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI Recommend Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={"name": "Steel Bar", "unit": "ton", "price": "500"}, headers=staff)

    fake = use_llm(FakeLLM(response=reply(text("Good fit for steel procurement."))))
    res = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
    assert res.status_code == 200, res.text
    assert "500" in fake.calls[0]["messages"][0]["content"]  # the real product price was included, not re-derived


# ---- Supplier portal ---------------------------------------------------------------------------


def test_supplier_ai_rfq_summary(client, auth_a, use_llm):
    staff, mkt_supplier, headers = onboarded_supplier(client, "ai1", name="AI Supplier Co", email="ai1@aisupplierco.com")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)

    fake = use_llm(FakeLLM(response=reply(text("Checklist: confirm pricing and delivery."))))
    res = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/ai/summary", headers=headers)
    assert res.status_code == 200, res.text
    assert "Checklist" in res.json()["narration"]


def test_supplier_ai_cannot_summarize_an_uninvited_rfq(client, auth_a, use_llm):
    staff, _mkt_supplier, headers = onboarded_supplier(client, "ai2", name="AI Uninvited Co", email="ai2@aiuninvited.com")
    project = make(client, auth_a, "/projects", {"name": "Uninvited Proj", "code": "AIUN", "budget": "1"})
    material = make(client, auth_a, "/materials", {"name": "M", "sku": "AIUNM", "unit": "kg"})
    rfq = make(client, auth_a, "/rfqs", {"title": "Not invited", "project_id": project["id"], "items": [{"material_id": material["id"], "quantity": "1"}]})

    use_llm(FakeLLM(response=reply(text("summary"))))
    res = client.get(f"/api/v1/supplier-portal/rfqs/{rfq['id']}/ai/summary", headers=headers)
    assert res.status_code == 404


# ---- Platform admin ----------------------------------------------------------------------------


def test_platform_crm_lead_insights(client, use_llm):
    staff = owner_headers(client, email="ai-staff6@buildos.ai")
    res = client.post("/api/v1/platform/crm/organizations", json={"name": "AI Lead Co", "pipeline_type": "saas_sales"}, headers=staff)
    org_id = res.json()["id"]

    fake = use_llm(FakeLLM(response=reply(text("This lead is new; suggest an intro call."))))
    res = client.post(f"/api/v1/platform/ai/crm-organizations/{org_id}/insights", json={}, headers=staff)
    assert res.status_code == 200, res.text
    assert "AI Lead Co" in fake.calls[0]["messages"][0]["content"]


def test_platform_revenue_summary_never_sums_saas_and_commission_revenue_as_one_figure(client, use_llm):
    staff = owner_headers(client, email="ai-staff7@buildos.ai")
    fake = use_llm(FakeLLM(response=reply(text("SaaS and commission revenue summarized separately."))))
    res = client.get("/api/v1/platform/ai/revenue-summary", headers=staff)
    assert res.status_code == 200, res.text
    assert "SaaS subscription revenue" in fake.calls[0]["messages"][0]["content"]
    assert "Marketplace commission revenue" in fake.calls[0]["messages"][0]["content"]


def test_platform_ai_endpoints_require_platform_token(client):
    res = client.get("/api/v1/platform/ai/revenue-summary")
    assert res.status_code == 401


def test_ai_narration_usage_is_rate_limited(client, auth_a, use_llm):
    staff = owner_headers(client, email="ai-staff8@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="AI Limit Co")
    _company_id, rfq = _invited_rfq(client, auth_a, staff, mkt_supplier)
    use_llm(FakeLLM(response=reply(text("summary"))))

    last = None
    for _ in range(35):
        last = client.get(f"/api/v1/rfqs/{rfq['id']}/ai/summary", headers=auth_a)
    assert last.status_code == 429
