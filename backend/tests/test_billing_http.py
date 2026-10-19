"""SaaS subscriptions and billing (PLAT-028..032): plans, lifecycle state
machine, manual payments, entitlements, legacy grandfathering, and
compatibility with the existing ERP."""

import io
from decimal import Decimal

from app.models.enums import PlatformStaffRole
from tests.test_marketplace_integration_http import owner_headers


def create_plan(client, staff, name="Starter", trial_days=0, max_projects=2, max_team_members=3, marketplace_included=False, monthly=Decimal("50")):
    res = client.post(
        "/api/v1/platform/billing/plans",
        json={
            "name": name, "trial_days": trial_days, "max_projects": max_projects, "max_team_members": max_team_members,
            "marketplace_included": marketplace_included,
            "prices": [{"currency": "USD", "billing_period": "monthly", "amount": str(monthly)}, {"currency": "USD", "billing_period": "annual", "amount": str(monthly * 10)}],
        },
        headers=staff,
    )
    assert res.status_code == 201, res.text
    return res.json()


# ---- PLAT-028: plans and pricing -----------------------------------------------------------


def test_create_plan_with_monthly_and_annual_pricing(client):
    staff = owner_headers(client, email="billing-staff1@buildos.ai")
    plan = create_plan(client, staff, name="Growth", monthly=Decimal("100"))
    prices = {p["billing_period"]: Decimal(p["amount"]) for p in plan["prices"]}
    assert prices["monthly"] == 100
    assert prices["annual"] == 1000


def test_updating_a_plan_versions_the_price_not_edits_it(client):
    staff = owner_headers(client, email="billing-staff2@buildos.ai")
    plan = create_plan(client, staff, name="Enterprise", monthly=Decimal("200"))
    res = client.post(f"/api/v1/platform/billing/plans/{plan['id']}/prices", json={"currency": "USD", "billing_period": "monthly", "amount": "250"}, headers=staff)
    assert res.status_code == 201
    monthly_prices = [p for p in res.json()["prices"] if p["billing_period"] == "monthly" and p["currency"] == "USD"]
    assert len(monthly_prices) == 2  # old one kept, not deleted
    current = [p for p in monthly_prices if p["is_current"]]
    assert len(current) == 1
    assert Decimal(current[0]["amount"]) == 250


def test_editing_plan_fields(client):
    staff = owner_headers(client, email="billing-staff3@buildos.ai")
    plan = create_plan(client, staff, name="Editable")
    res = client.patch(f"/api/v1/platform/billing/plans/{plan['id']}", json={"max_projects": 10, "is_active": False}, headers=staff)
    assert res.status_code == 200
    assert res.json()["max_projects"] == 10
    assert res.json()["is_active"] is False


def test_frontend_never_needs_hardcoded_limits_plans_are_fully_api_driven(client, auth_a):
    staff = owner_headers(client, email="billing-staff4@buildos.ai")
    create_plan(client, staff, name="Visible Plan")
    res = client.get("/api/v1/billing/plans", headers=auth_a)
    assert res.status_code == 200
    assert any(p["name"] == "Visible Plan" for p in res.json())


# ---- PLAT-029: subscription lifecycle --------------------------------------------------------


def test_trial_subscription_activation(client, auth_a):
    staff = owner_headers(client, email="billing-staff5@buildos.ai")
    plan = create_plan(client, staff, name="Trial Plan", trial_days=14)
    res = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    assert res.status_code == 201, res.text
    sub = res.json()
    assert sub["status"] == "trialing"
    assert sub["trial_ends_at"] is not None


def test_no_trial_plan_starts_pending_payment_and_generates_an_invoice(client, auth_a):
    staff = owner_headers(client, email="billing-staff6@buildos.ai")
    plan = create_plan(client, staff, name="No Trial Plan", trial_days=0, monthly=Decimal("75"))
    res = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    assert res.status_code == 201
    assert res.json()["status"] == "pending_payment"

    res = client.get("/api/v1/billing/invoices", headers=auth_a)
    assert res.status_code == 200
    invoices = res.json()
    assert len(invoices) == 1
    assert Decimal(invoices[0]["total_amount"]) == 75


def test_a_company_has_at_most_one_live_subscription_at_a_time(client, auth_a):
    staff = owner_headers(client, email="billing-staff7@buildos.ai")
    plan = create_plan(client, staff, name="Only One A")
    res1 = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    assert res1.status_code == 201
    plan2 = create_plan(client, staff, name="Only One B")
    res2 = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan2["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    assert res2.status_code == 409  # DB-level unique index catches this, not just an app check


def test_plan_upgrade_and_downgrade(client, auth_a):
    staff = owner_headers(client, email="billing-staff8@buildos.ai")
    plan_a = create_plan(client, staff, name="Upgrade From", trial_days=7)
    plan_b = create_plan(client, staff, name="Upgrade To", trial_days=7, max_projects=50)
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan_a["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a).json()
    res = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/change-plan", json={"plan_id": plan_b["id"]}, headers=auth_a)
    assert res.status_code == 200, res.text
    assert res.json()["plan_name"] == "Upgrade To"


def test_cancellation(client, auth_a):
    staff = owner_headers(client, email="billing-staff9@buildos.ai")
    plan = create_plan(client, staff, name="Cancel Me", trial_days=7)
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a).json()
    res = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/cancel", headers=auth_a)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # After cancelling, the company can start a fresh subscription -- the slot is free again.
    plan2 = create_plan(client, staff, name="After Cancel")
    res = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan2["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    assert res.status_code == 201


def test_invalid_transitions_are_refused(client, auth_a):
    staff = owner_headers(client, email="billing-staff10@buildos.ai")
    plan = create_plan(client, staff, name="Bad Transition", trial_days=7)
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a).json()
    client.post(f"/api/v1/billing/subscriptions/{sub['id']}/cancel", headers=auth_a)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    # Cancelled is terminal -- can't be moved to grace period.
    res = client.post(f"/api/v1/platform/billing/companies/{company_id}/subscriptions/{sub['id']}/grace-period", headers=staff)
    assert res.status_code == 400


def test_renewal_via_grace_period_and_expiration(client, auth_a):
    # Realistic lifecycle: grace period only ever follows an ACTIVE or
    # PENDING_PAYMENT subscription (a renewal payment that didn't come in on
    # time), never straight from TRIALING -- enforced by the state machine
    # itself, not just this test's setup.
    staff = owner_headers(client, email="billing-staff11@buildos.ai")
    plan = create_plan(client, staff, name="Grace Plan", trial_days=0, monthly=Decimal("25"))
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a).json()
    assert sub["status"] == "pending_payment"
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.post(f"/api/v1/platform/billing/companies/{company_id}/subscriptions/{sub['id']}/grace-period", headers=staff)
    assert res.status_code == 200
    assert res.json()["status"] == "grace_period"
    assert res.json()["grace_period_ends_at"] is not None

    res = client.post(f"/api/v1/platform/billing/companies/{company_id}/subscriptions/{sub['id']}/expire", headers=staff)
    assert res.status_code == 200
    assert res.json()["status"] == "expired"


def test_subscription_history_is_recorded(client, auth_a):
    staff = owner_headers(client, email="billing-staff12@buildos.ai")
    plan = create_plan(client, staff, name="History Plan", trial_days=7)
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a).json()
    client.post(f"/api/v1/billing/subscriptions/{sub['id']}/cancel", headers=auth_a)
    res = client.get(f"/api/v1/billing/subscriptions/{sub['id']}/events", headers=auth_a)
    assert res.status_code == 200
    event_types = [e["event_type"] for e in res.json()]
    assert "subscription.created" in event_types
    assert "subscription.cancelled" in event_types


# ---- PLAT-030: invoices and manual payments ---------------------------------------------------


def _subscribed_company(client, staff, monthly=Decimal("60")):
    from tests.conftest import register

    headers = register(client, "PAYCO", "payco-admin@example.com")
    plan = create_plan(client, staff, name=f"PayPlan-{monthly}", trial_days=0, monthly=monthly)
    sub = client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=headers).json()
    invoice = client.get("/api/v1/billing/invoices", headers=headers).json()[0]
    return headers, invoice


def test_manual_payment_submission_and_verification_activates_the_subscription(client):
    staff = owner_headers(client, email="billing-staff13@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("60"))

    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments",
        data={"amount": "60", "reference": "TXN-001"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    submission = res.json()
    assert submission["status"] == "pending"

    res = client.get("/api/v1/platform/billing/payments/pending", headers=staff)
    assert any(p["id"] == submission["id"] for p in res.json())

    res = client.post(f"/api/v1/platform/billing/payments/{submission['id']}/verify", headers=staff)
    assert res.status_code == 200
    assert res.json()["status"] == "verified"

    res = client.get(f"/api/v1/billing/invoices/{invoice['id']}", headers=headers)
    assert res.json()["status"] == "paid"

    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["status"] == "active"


def test_duplicate_verification_is_refused(client):
    staff = owner_headers(client, email="billing-staff14@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("40"))
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "40"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = res.json()["id"]
    res1 = client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=staff)
    assert res1.status_code == 200
    res2 = client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=staff)
    assert res2.status_code == 409  # can't verify twice, can't double-activate


def test_payment_rejection_with_reason(client):
    staff = owner_headers(client, email="billing-staff15@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("30"))
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "30"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = res.json()["id"]
    res = client.post(f"/api/v1/platform/billing/payments/{submission_id}/reject", json={"reason": "Amount doesn't match"}, headers=staff)
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    assert res.json()["rejection_reason"] == "Amount doesn't match"

    # Invoice stays unpaid, subscription stays pending -- rejection doesn't activate anything.
    res = client.get(f"/api/v1/billing/invoices/{invoice['id']}", headers=headers)
    assert res.json()["status"] == "pending"


def test_support_staff_cannot_verify_payments(client):
    owner = owner_headers(client, email="billing-staff16@buildos.ai")
    support = __import__("tests.test_platform_http", fromlist=["platform_login"]).platform_login(client, email="billing-support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    headers, invoice = _subscribed_company(client, owner, Decimal("20"))
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "20"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = res.json()["id"]
    res = client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=support)
    assert res.status_code == 403


def test_company_users_cannot_verify_their_own_payment(client):
    """There is no tenant-side verify endpoint at all -- the only verify route
    lives under /platform/billing and requires a platform staff token, which a
    company user's tenant token can never satisfy (same separation as every
    other platform/tenant boundary in this app)."""
    staff = owner_headers(client, email="billing-staff17@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("20"))
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "20"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = res.json()["id"]
    res = client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=headers)
    assert res.status_code == 401  # a tenant token on a platform-only route


def test_invoice_download_and_proof_round_trip(client):
    staff = owner_headers(client, email="billing-staff18@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("15"))
    proof_bytes = b"%PDF-1.4\nreal content"
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "15"},
        files={"file": ("proof.pdf", io.BytesIO(proof_bytes), "application/pdf")}, headers=headers,
    )
    submission_id = res.json()["id"]
    res = client.get(f"/api/v1/billing/payments/{submission_id}/proof", headers=headers)
    assert res.status_code == 200
    assert res.content == proof_bytes

    res = client.get(f"/api/v1/billing/invoices/{invoice['id']}", headers=headers)
    assert res.status_code == 200
    assert Decimal(res.json()["total_amount"]) == 15


# ---- Security / isolation ----------------------------------------------------------------------


def test_company_a_cannot_view_company_b_invoices(client, auth_a, auth_b):
    staff = owner_headers(client, email="billing-staff19@buildos.ai")
    plan = create_plan(client, staff, name="Isolation Plan", trial_days=0, monthly=Decimal("10"))
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    invoice = client.get("/api/v1/billing/invoices", headers=auth_a).json()[0]

    res = client.get(f"/api/v1/billing/invoices/{invoice['id']}", headers=auth_b)
    assert res.status_code == 404
    assert client.get("/api/v1/billing/invoices", headers=auth_b).json() == []


# ---- PLAT-031: entitlements and usage limits ----------------------------------------------------


def test_backend_enforced_project_limit(client, auth_a, viewer_a=None):
    staff = owner_headers(client, email="billing-staff20@buildos.ai")
    plan = create_plan(client, staff, name="Tiny Plan", trial_days=7, max_projects=1)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)

    res = client.post("/api/v1/projects", json={"name": "First", "code": "P1", "budget": "1"}, headers=auth_a)
    assert res.status_code == 201
    res = client.post("/api/v1/projects", json={"name": "Second", "code": "P2", "budget": "1"}, headers=auth_a)
    assert res.status_code == 403
    assert "limit" in res.json()["detail"].lower()


def test_entitlements_endpoint_reflects_real_usage(client, auth_a):
    staff = owner_headers(client, email="billing-staff21@buildos.ai")
    plan = create_plan(client, staff, name="Usage Plan", trial_days=7, max_projects=5)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    client.post("/api/v1/projects", json={"name": "A Project", "code": "AP1", "budget": "1"}, headers=auth_a)

    res = client.get("/api/v1/billing/entitlements", headers=auth_a)
    assert res.status_code == 200
    body = res.json()
    assert body["source"] == "subscription"
    assert body["max_projects"] == 5
    assert body["current_projects"] == 1


# ---- PLAT-032: legacy company protection ----------------------------------------------------------


def test_a_company_with_no_subscription_is_never_blocked_same_as_before_phase_5(client, auth_a):
    """The critical compatibility guarantee: a company that never subscribes
    to anything keeps working exactly as it did before billing existed --
    discovered the hard way while building this (see the daily log)."""
    res = client.post("/api/v1/projects", json={"name": "Unrestricted", "code": "UNR1", "budget": "1"}, headers=auth_a)
    assert res.status_code == 201
    res = client.get("/api/v1/billing/entitlements", headers=auth_a)
    assert res.json()["source"] == "none"
    assert res.json()["max_projects"] is None


def test_marketplace_flag_still_works_standalone_without_any_subscription(client, auth_a):
    """Day 33's marketplace_enabled flag, used completely on its own (no
    subscription involved at all) -- must behave exactly as it did when it
    was built, since this company has no subscription and no legacy record."""
    staff = owner_headers(client, email="billing-staff22@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is False
    client.post(f"/api/v1/platform/companies/{company_id}/marketplace", json={"enabled": True}, headers=staff)
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is True


def test_a_real_subscription_without_marketplace_included_still_needs_the_operational_flag_and_the_plan(client, auth_a):
    staff = owner_headers(client, email="billing-staff23@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    client.post(f"/api/v1/platform/companies/{company_id}/marketplace", json={"enabled": True}, headers=staff)

    plan = create_plan(client, staff, name="No Marketplace Plan", trial_days=7, marketplace_included=False)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is False  # operational flag on, but this plan doesn't include it

    plan2 = create_plan(client, staff, name="Marketplace Plan", trial_days=7, marketplace_included=True)
    sub = client.get("/api/v1/billing/subscription", headers=auth_a).json()
    client.post(f"/api/v1/billing/subscriptions/{sub['id']}/change-plan", json={"plan_id": plan2["id"]}, headers=auth_a)
    res = client.get("/api/v1/marketplace/status", headers=auth_a)
    assert res.json()["enabled"] is True


def test_legacy_entitlements_are_listed_for_staff_review(client):
    """The migration grandfathers real pre-existing companies in Postgres;
    under the test suite's SQLite schema (built from models, not via Alembic)
    no legacy rows exist yet -- this just proves the review endpoint itself
    works and returns real data once a row exists."""
    staff = owner_headers(client, email="billing-staff24@buildos.ai")
    res = client.get("/api/v1/platform/billing/legacy-entitlements", headers=staff)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ---- Dashboards -----------------------------------------------------------------------------------


def test_billing_overview_dashboard(client, auth_a):
    staff = owner_headers(client, email="billing-staff25@buildos.ai")
    plan = create_plan(client, staff, name="Overview Plan", trial_days=7)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    res = client.get("/api/v1/platform/billing/overview", headers=staff)
    assert res.status_code == 200
    assert res.json()["trialing_subscriptions"] >= 1


# ---- Phase 5.1: company subscriptions directory and detail (Task 1) ----------------------------


def test_company_billing_directory_search_and_filter(client, auth_a):
    staff = owner_headers(client, email="billing-staff26@buildos.ai")
    plan = create_plan(client, staff, name="Directory Plan", trial_days=7, monthly=Decimal("25"))
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.get("/api/v1/platform/billing/companies", headers=staff)
    assert res.status_code == 200
    row = next(r for r in res.json() if r["company_id"] == company_id)
    assert row["plan_name"] == "Directory Plan"
    assert row["status"] == "trialing"

    res = client.get("/api/v1/platform/billing/companies", params={"search": "Company AAA"}, headers=staff)
    assert any(r["company_id"] == company_id for r in res.json())
    res = client.get("/api/v1/platform/billing/companies", params={"search": "No Such Company"}, headers=staff)
    assert res.json() == []

    res = client.get("/api/v1/platform/billing/companies", params={"plan_id": plan["id"]}, headers=staff)
    assert all(r["plan_id"] == plan["id"] for r in res.json())
    res = client.get("/api/v1/platform/billing/companies", params={"status": "trialing"}, headers=staff)
    assert all(r["status"] == "trialing" for r in res.json())


def test_company_billing_summary_detail_view(client, auth_a):
    staff = owner_headers(client, email="billing-staff27@buildos.ai")
    plan = create_plan(client, staff, name="Detail Plan", trial_days=7)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.get(f"/api/v1/platform/billing/companies/{company_id}/summary", headers=staff)
    assert res.status_code == 200
    body = res.json()
    assert body["plan_name"] == "Detail Plan"
    assert body["is_legacy"] is False

    res = client.get(f"/api/v1/platform/billing/companies/{company_id}/subscriptions", headers=staff)
    assert len(res.json()) == 1
    res = client.get(f"/api/v1/platform/billing/companies/{company_id}/events", headers=staff)
    assert any(e["event_type"] == "subscription.created" for e in res.json())


def test_a_company_with_no_subscription_shows_up_as_none_in_the_directory(client, auth_a):
    """PLAT-032 compatibility: a plain company shouldn't vanish from the
    staff directory just because it never subscribed to anything."""
    staff = owner_headers(client, email="billing-staff28@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get(f"/api/v1/platform/billing/companies/{company_id}/summary", headers=staff)
    assert res.json()["status"] == "none"
    assert res.json()["is_legacy"] is False


def test_new_companies_are_not_automatically_grandfathered(client, auth_a):
    """The explicit requirement from the Phase 5.1 brief: grandfathering is a
    one-time data migration against companies that already existed, never
    something a fresh registration gets for free."""
    staff = owner_headers(client, email="billing-staff29@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get("/api/v1/platform/billing/legacy-entitlements", headers=staff)
    assert not any(e["company_id"] == company_id for e in res.json())


# ---- Phase 5.1: platform-wide invoice management (Task 2) --------------------------------------


def test_platform_wide_invoice_list_filters_by_company_and_status(client, auth_a, auth_b):
    staff = owner_headers(client, email="billing-staff30@buildos.ai")
    plan_a = create_plan(client, staff, name="Invoices A", trial_days=0, monthly=Decimal("10"))
    plan_b = create_plan(client, staff, name="Invoices B", trial_days=0, monthly=Decimal("20"))
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan_a["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan_b["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_b)
    company_a = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.get("/api/v1/platform/billing/invoices", headers=staff)
    assert res.status_code == 200
    assert len(res.json()) >= 2
    assert all("company_name" in inv for inv in res.json())

    res = client.get("/api/v1/platform/billing/invoices", params={"company_id": company_a}, headers=staff)
    assert all(inv["company_id"] == company_a for inv in res.json())
    assert len(res.json()) == 1

    res = client.get("/api/v1/platform/billing/invoices", params={"status": "pending"}, headers=staff)
    assert all(inv["status"] == "pending" for inv in res.json())
    assert len(res.json()) >= 2


# ---- Phase 5.1: revenue dashboard (Task 3) ------------------------------------------------------


def test_revenue_dashboard_calculates_mrr_from_active_subscriptions_not_payment_totals(client):
    staff = owner_headers(client, email="billing-staff31@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("99"))

    # Still pending payment -- not active yet, so it must not count toward MRR.
    res = client.get("/api/v1/platform/billing/revenue", headers=staff)
    before = next((p["count"] for p in res.json()["plan_distribution"] if p["plan_name"].startswith("PayPlan")), 0)
    assert before >= 1  # counted in plan distribution (a live subscription)

    client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "99"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = client.get("/api/v1/platform/billing/payments/pending", headers=staff).json()[-1]["id"]
    client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=staff)

    res = client.get("/api/v1/platform/billing/revenue", headers=staff)
    body = res.json()
    assert Decimal(body["mrr"]) >= Decimal("99")  # now active, so it IS recognized MRR
    assert Decimal(body["revenue_collected"]) >= Decimal("99")  # and a real cash receipt
    assert any(point["amount"] for point in body["monthly_trend"])


# ---- Phase 5.1: company renewal flow (Task 5) ---------------------------------------------------


def test_renewal_invoice_is_idempotent_on_repeated_requests(client):
    staff = owner_headers(client, email="billing-staff32@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("77"))
    sub = client.get("/api/v1/billing/subscription", headers=headers).json()

    # Still pending_payment, which is a valid state to (re-)request the same
    # invoice from -- this must return the SAME invoice, not create a second one.
    res1 = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/renew", headers=headers)
    assert res1.status_code == 200
    res2 = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/renew", headers=headers)
    assert res2.status_code == 200
    assert res1.json()["id"] == res2.json()["id"]

    all_invoices = client.get("/api/v1/billing/invoices", headers=headers).json()
    assert len(all_invoices) == 1  # no duplicate created


def test_renewal_after_activation_generates_a_fresh_invoice_and_is_logged(client):
    staff = owner_headers(client, email="billing-staff33@buildos.ai")
    headers, invoice = _subscribed_company(client, staff, Decimal("55"))
    client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "55"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=headers,
    )
    submission_id = client.get("/api/v1/platform/billing/payments/pending", headers=staff).json()[-1]["id"]
    client.post(f"/api/v1/platform/billing/payments/{submission_id}/verify", headers=staff)

    sub = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert sub["status"] == "active"
    res = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/renew", headers=headers)
    assert res.status_code == 200
    renewal_invoice = res.json()
    assert renewal_invoice["id"] != invoice["id"]  # a real second invoice for the next period

    events = client.get(f"/api/v1/billing/subscriptions/{sub['id']}/events", headers=headers).json()
    assert any(e["event_type"] == "subscription.renewal_invoice_requested" for e in events)

    # Asking again before paying the renewal invoice must not create a third one.
    res2 = client.post(f"/api/v1/billing/subscriptions/{sub['id']}/renew", headers=headers)
    assert res2.json()["id"] == renewal_invoice["id"]
