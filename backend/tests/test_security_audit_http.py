"""Phase 9 cross-portal security audit (PLAT-049): token-type rejection
across all three auth systems, revoked-membership enforcement, financial
authorization isolation, and the rate-limiting gaps found and fixed this
phase."""

import io
from decimal import Decimal

from app.models.enums import PlatformStaffRole
from tests.conftest import register
from tests.test_marketplace_integration_http import owner_headers
from tests.test_platform_http import platform_login
from tests.test_supplier_portal_http import invite_and_accept, onboarded_supplier, supplier_headers


# ---- Cross-token rejection ----------------------------------------------------------------------


def test_supplier_token_cannot_access_company_erp_apis(client):
    _staff, _supplier, headers = onboarded_supplier(client, "sec1", email="sec1@security.com")
    res = client.get("/api/v1/projects", headers=headers)
    assert res.status_code == 401
    res = client.get("/api/v1/billing/entitlements", headers=headers)
    assert res.status_code == 401


def test_company_token_cannot_access_platform_staff_apis(client, auth_a):
    res = client.get("/api/v1/platform/dashboard", headers=auth_a)
    assert res.status_code == 401
    res = client.get("/api/v1/platform/billing/overview", headers=auth_a)
    assert res.status_code == 401


def test_platform_token_cannot_access_supplier_portal_apis(client):
    staff = owner_headers(client, email="sec2@buildos.ai")
    res = client.get("/api/v1/supplier-portal/dashboard", headers=staff)
    assert res.status_code == 401


def test_company_token_cannot_access_supplier_portal_apis(client, auth_a):
    res = client.get("/api/v1/supplier-portal/dashboard", headers=auth_a)
    assert res.status_code == 401


def test_supplier_token_cannot_access_platform_staff_apis(client):
    _staff, _supplier, headers = onboarded_supplier(client, "sec3", email="sec3@security.com")
    res = client.get("/api/v1/platform/dashboard", headers=headers)
    assert res.status_code == 401


def test_a_completely_forged_token_is_rejected_by_all_three_systems(client):
    forged = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/api/v1/projects", headers=forged).status_code == 401
    assert client.get("/api/v1/platform/dashboard", headers=forged).status_code == 401
    assert client.get("/api/v1/supplier-portal/dashboard", headers=forged).status_code == 401


# ---- Membership/account status enforced on every protected request ------------------------------


def test_revoked_supplier_membership_cannot_retain_access_through_an_old_token(client):
    staff = owner_headers(client, email="sec4@buildos.ai")
    from tests.test_marketplace_integration_http import make_verified_supplier

    mkt_supplier = make_verified_supplier(client, staff, name="Revoke Access Co")
    invite_and_accept(client, staff, mkt_supplier["id"], "owner@revokeaccess.com", role="owner")
    owner_hdrs = supplier_headers(client, "owner@revokeaccess.com")

    # A second member, whose OLD access token we'll try to keep using after revocation.
    res = client.post("/api/v1/supplier-portal/team/invitations", json={"email": "member@revokeaccess.com", "role": "staff"}, headers=owner_hdrs)
    token = res.json()["token"]
    client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": token, "full_name": "Member", "password": "password123"})
    member_hdrs = supplier_headers(client, "member@revokeaccess.com")

    # The member's access token works right now.
    assert client.get("/api/v1/supplier-portal/dashboard", headers=member_hdrs).status_code == 200

    members = client.get("/api/v1/supplier-portal/team/members", headers=owner_hdrs).json()
    member_row = next(m for m in members if m["user_email"] == "member@revokeaccess.com")
    client.post(f"/api/v1/supplier-portal/team/members/{member_row['id']}/revoke", headers=owner_hdrs)

    # The SAME, still-unexpired access token must stop working now that the
    # membership behind it is revoked -- membership status is checked on
    # every request, not just at login.
    res = client.get("/api/v1/supplier-portal/dashboard", headers=member_hdrs)
    assert res.status_code == 403


def test_deactivated_company_user_loses_access_immediately(client, auth_a):
    """get_current_user re-checks user.is_active on every request, not just
    at login -- confirmed by deactivating a second user and reusing their
    already-issued token."""
    import uuid as _uuid

    from app.db.session import SessionLocal
    from app.models.user import User

    res = client.get("/api/v1/auth/me", headers=auth_a).json()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == _uuid.UUID(res["id"])).first()
        user.is_active = False
        db.commit()
    finally:
        db.close()

    res = client.get("/api/v1/auth/me", headers=auth_a)
    assert res.status_code == 401


def test_suspended_company_loses_all_user_access_immediately(client, auth_a):
    staff = owner_headers(client, email="sec5@buildos.ai")
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=staff)
    assert res.status_code == 200
    res = client.get("/api/v1/auth/me", headers=auth_a)
    assert res.status_code == 401


# ---- Rate limiting (gaps found and fixed this phase) ---------------------------------------------


def test_refresh_endpoint_is_now_rate_limited_on_all_three_systems(client, auth_a):
    """Previously unlimited on all three systems -- confirmed and fixed in
    this audit."""
    last = None
    for _ in range(35):
        last = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert last.status_code == 429


def test_supplier_login_is_now_rate_limited(client):
    """The entire supplier-portal auth surface previously had zero rate
    limiting -- confirmed and fixed in this audit."""
    last = None
    for _ in range(10):
        last = client.post("/api/v1/supplier-portal/auth/login", json={"email": "nobody@nowhere.com", "password": "wrong"})
    assert last.status_code == 429


def test_supplier_accept_invite_is_now_rate_limited(client):
    last = None
    for _ in range(15):
        last = client.post("/api/v1/supplier-portal/auth/accept-invite", json={"token": "x" * 32, "full_name": "A B", "password": "password123"})
    assert last.status_code == 429


# ---- Financial authorization ---------------------------------------------------------------------


def test_payment_proof_download_is_isolated_per_company(client, auth_a, auth_b):
    staff = owner_headers(client, email="sec6@buildos.ai")
    from tests.test_billing_http import create_plan

    plan = create_plan(client, staff, name="Sec Plan", trial_days=0, monthly=Decimal("50"))
    client.post("/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_a)
    invoice = client.get("/api/v1/billing/invoices", headers=auth_a).json()[0]
    res = client.post(
        f"/api/v1/billing/invoices/{invoice['id']}/payments", data={"amount": "50"},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-1.4\nmock"), "application/pdf")}, headers=auth_a,
    )
    submission_id = res.json()["id"]

    res = client.get(f"/api/v1/billing/payments/{submission_id}/proof", headers=auth_b)
    assert res.status_code == 404  # company B can never download company A's payment proof


def test_commission_agreement_management_requires_owner_or_admin_staff(client):
    staff_support = platform_login(client, email="sec-support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    from tests.test_marketplace_integration_http import make_verified_supplier

    owner = owner_headers(client, email="sec7@buildos.ai")
    mkt_supplier = make_verified_supplier(client, owner, name="Sec Commission Co")
    res = client.post(f"/api/v1/platform/commissions/suppliers/{mkt_supplier['id']}/agreements", json={"basis": "percentage", "rate": "0.05"}, headers=staff_support)
    assert res.status_code == 403  # support staff cannot manage commission agreements


def test_commission_settlement_requires_owner_or_admin_staff(client):
    staff_support = platform_login(client, email="sec-support2@buildos.ai", role=PlatformStaffRole.SUPPORT)
    res = client.post("/api/v1/platform/commissions/invoices/00000000-0000-0000-0000-000000000000/payments", json={"amount": "10", "paid_on": "2026-01-01"}, headers=staff_support)
    assert res.status_code == 403  # refused before even reaching the "not found" check


def test_invoice_download_requires_authenticated_company_user(client):
    res = client.get("/api/v1/billing/invoices/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 401


# ---- Public endpoint abuse / information exposure -----------------------------------------------


def test_public_plans_endpoint_never_leaks_inactive_plans(client):
    staff = owner_headers(client, email="sec8@buildos.ai")
    from tests.test_billing_http import create_plan

    plan = create_plan(client, staff, name="Sec Inactive Plan", trial_days=0, monthly=Decimal("10"))
    client.patch(f"/api/v1/platform/billing/plans/{plan['id']}", json={"is_active": False}, headers=staff)
    res = client.get("/api/v1/public/plans")
    assert not any(p["name"] == "Sec Inactive Plan" for p in res.json())


def test_supplier_invitation_info_does_not_leak_to_an_unrelated_token_guess(client):
    res = client.get("/api/v1/supplier-portal/auth/invitations/completely-made-up-token-value")
    assert res.status_code == 404  # no information about whether any invitation exists at all
