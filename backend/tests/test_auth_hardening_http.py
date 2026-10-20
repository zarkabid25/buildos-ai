"""Phase 9.1 (Task 1 & 4): server-side token revocation, refresh rotation
and reuse detection, logout/logout-all, session invalidation on password
change and suspension, and centralized AI usage quota enforcement."""

from decimal import Decimal


def _register(client, code, email):
    res = client.post(
        "/api/v1/auth/register",
        json={"company_name": f"Co {code}", "company_code": code, "full_name": "Admin", "email": email, "password": "password123"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    return body["access_token"], body["refresh_token"], body["user"]["id"], body["user"]["company_id"]


# ---- Refresh rotation and reuse detection ---------------------------------------------------


def test_refresh_token_rotates_and_the_old_one_cannot_be_reused(client):
    _access, refresh, _uid, _cid = _register(client, "ROT1", "rot1@example.com")

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert first.status_code == 200, first.text
    new_refresh = first.json()["refresh_token"]
    assert new_refresh != refresh

    # Replaying the original (already-rotated-away) refresh token must fail.
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401

    # And the reuse must have poisoned the whole session: even the token
    # that was correctly issued from the rotation no longer works.
    poisoned = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert poisoned.status_code == 401


def test_platform_and_supplier_refresh_also_rotate(client):
    from tests.test_marketplace_integration_http import owner_headers
    from tests.test_platform_http import platform_login
    from tests.test_supplier_portal_http import onboarded_supplier

    # Platform staff refresh rotation.
    owner_headers(client, email="rot2@buildos.ai")  # ensures at least one admin exists
    login = client.post("/api/v1/platform/auth/login", json={"email": "rot2@buildos.ai", "password": "password123"})
    refresh = login.json()["refresh_token"]
    first = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": refresh})
    assert first.status_code == 200, first.text
    reused = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401


# ---- Logout and logout-all -----------------------------------------------------------------


def test_logout_revokes_the_access_token_used_to_call_it(client):
    access, _refresh, _uid, _cid = _register(client, "LOGOUT1", "logout1@example.com")
    headers = {"Authorization": f"Bearer {access}"}

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_logout_all_invalidates_every_previously_issued_token(client):
    access, refresh, _uid, _cid = _register(client, "LOGOUTALL1", "logoutall1@example.com")
    headers = {"Authorization": f"Bearer {access}"}

    # A second access token for the same user, from a second "device".
    second_login = client.post("/api/v1/auth/login", json={"email": "logoutall1@example.com", "password": "password123"})
    second_access = second_login.json()["access_token"]
    second_headers = {"Authorization": f"Bearer {second_access}"}
    assert client.get("/api/v1/auth/me", headers=second_headers).status_code == 200

    assert client.post("/api/v1/auth/logout-all", headers=headers).status_code == 204

    # Both the calling session and the other "device"'s session are dead now.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/auth/me", headers=second_headers).status_code == 401
    # So is the original refresh token.
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_password_change_invalidates_existing_sessions(client):
    access, _refresh, _uid, _cid = _register(client, "PWCHANGE1", "pwchange1@example.com")
    headers = {"Authorization": f"Bearer {access}"}

    res = client.post(
        "/api/v1/auth/me/password", json={"current_password": "password123", "new_password": "newpassword456"}, headers=headers,
    )
    assert res.status_code == 204, res.text

    # The token used to change the password is now dead too -- not just
    # other sessions -- since the change invalidates the whole subject.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    # A fresh login with the new password still works.
    relogin = client.post("/api/v1/auth/login", json={"email": "pwchange1@example.com", "password": "newpassword456"})
    assert relogin.status_code == 200


def test_company_suspension_invalidates_every_users_session_immediately(client):
    from tests.test_marketplace_integration_http import owner_headers

    access, _refresh, _uid, company_id = _register(client, "SUSP1", "susp1@example.com")
    headers = {"Authorization": f"Bearer {access}"}
    staff = owner_headers(client, email="susp-staff@buildos.ai")

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    res = client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=staff)
    assert res.status_code == 200, res.text
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_supplier_portal_logout_and_logout_all(client):
    from tests.test_supplier_portal_http import onboarded_supplier

    _staff, _supplier, headers = onboarded_supplier(client, "rothard", email="rothard@security.com")
    assert client.get("/api/v1/supplier-portal/dashboard", headers=headers).status_code == 200
    assert client.post("/api/v1/supplier-portal/auth/logout-all", headers=headers).status_code == 204
    assert client.get("/api/v1/supplier-portal/dashboard", headers=headers).status_code == 401


# ---- AI usage quota (Task 4) -----------------------------------------------------------------


def _subscribe_with_ai_limit(client, staff_headers, auth_headers, limit: int):
    from tests.test_billing_http import create_plan

    plan = create_plan(client, staff_headers, name=f"AI Capped Plan {limit}", trial_days=0, monthly=Decimal("10"), marketplace_included=True)
    patched = client.patch(f"/api/v1/platform/billing/plans/{plan['id']}", json={"ai_monthly_messages": limit}, headers=staff_headers)
    assert patched.status_code == 200, patched.text
    res = client.post(
        "/api/v1/billing/subscriptions", json={"plan_id": plan["id"], "billing_period": "monthly", "currency": "USD"}, headers=auth_headers,
    )
    assert res.status_code == 201, res.text


def test_ai_quota_blocks_once_the_plan_limit_is_reached(client, auth_a, use_llm=None):
    from app.ai.llm import get_llm_dependency
    from app.main import app
    from tests.test_ai_narration_http import FakeLLM, reply, text
    from tests.test_marketplace_integration_http import enable_marketplace, make, make_verified_supplier, owner_headers

    staff = owner_headers(client, email="quota1@buildos.ai")
    _subscribe_with_ai_limit(client, staff, auth_a, limit=1)

    mkt_supplier = make_verified_supplier(client, staff, name="Quota Supplier Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={"name": "Rebar", "unit": "ton", "price": "400"}, headers=staff)

    fake = FakeLLM(response=reply(text("Good fit.")))
    app.dependency_overrides[get_llm_dependency] = lambda: fake
    try:
        first = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
        assert first.status_code == 200, first.text
        second = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
        assert second.status_code == 429
    finally:
        app.dependency_overrides.pop(get_llm_dependency, None)


def test_ai_quota_is_isolated_per_company(client, auth_a, auth_b):
    from app.ai.llm import get_llm_dependency
    from app.main import app
    from tests.test_ai_narration_http import FakeLLM, reply, text
    from tests.test_marketplace_integration_http import enable_marketplace, make_verified_supplier, owner_headers

    staff = owner_headers(client, email="quota2@buildos.ai")
    _subscribe_with_ai_limit(client, staff, auth_a, limit=1)

    mkt_supplier = make_verified_supplier(client, staff, name="Quota Isolation Co")
    enable_marketplace(client, staff, auth_a)
    enable_marketplace(client, staff, auth_b)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={"name": "Pipe", "unit": "m", "price": "20"}, headers=staff)

    fake = FakeLLM(response=reply(text("Good fit.")))
    app.dependency_overrides[get_llm_dependency] = lambda: fake
    try:
        used_up = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
        assert used_up.status_code == 200, used_up.text
        exhausted = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
        assert exhausted.status_code == 429

        # Company B has never used its own quota -- a sibling company
        # hitting 429 must never affect it.
        still_fine = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_b)
        assert still_fine.status_code == 200, still_fine.text
    finally:
        app.dependency_overrides.pop(get_llm_dependency, None)


def test_ai_quota_unrestricted_without_a_live_subscription(client, auth_a):
    """source == "none" (no subscription at all) stays unrestricted, same
    rule entitlement_service already applies to project/team-member limits."""
    from app.ai.llm import get_llm_dependency
    from app.main import app
    from tests.test_ai_narration_http import FakeLLM, reply, text
    from tests.test_marketplace_integration_http import enable_marketplace, make_verified_supplier, owner_headers

    staff = owner_headers(client, email="quota3@buildos.ai")
    mkt_supplier = make_verified_supplier(client, staff, name="Quota Unrestricted Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={"name": "Sand", "unit": "ton", "price": "10"}, headers=staff)

    fake = FakeLLM(response=reply(text("Good fit.")))
    app.dependency_overrides[get_llm_dependency] = lambda: fake
    try:
        for _ in range(3):
            res = client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
            assert res.status_code == 200, res.text
    finally:
        app.dependency_overrides.pop(get_llm_dependency, None)


def test_entitlements_endpoint_reports_real_ai_usage(client, auth_a):
    from app.ai.llm import get_llm_dependency
    from app.main import app
    from tests.test_ai_narration_http import FakeLLM, reply, text
    from tests.test_marketplace_integration_http import enable_marketplace, make_verified_supplier, owner_headers

    staff = owner_headers(client, email="quota4@buildos.ai")
    _subscribe_with_ai_limit(client, staff, auth_a, limit=5)
    mkt_supplier = make_verified_supplier(client, staff, name="Quota Visibility Co")
    enable_marketplace(client, staff, auth_a)
    client.post(f"/api/v1/platform/marketplace/suppliers/{mkt_supplier['id']}/products", json={"name": "Brick", "unit": "pc", "price": "1"}, headers=staff)

    fake = FakeLLM(response=reply(text("Good fit.")))
    app.dependency_overrides[get_llm_dependency] = lambda: fake
    try:
        client.get(f"/api/v1/marketplace/suppliers/{mkt_supplier['id']}/ai/recommendation", headers=auth_a)
    finally:
        app.dependency_overrides.pop(get_llm_dependency, None)

    ent = client.get("/api/v1/billing/entitlements", headers=auth_a)
    assert ent.status_code == 200, ent.text
    assert ent.json()["current_ai_messages"] == 1
    assert ent.json()["ai_monthly_messages"] == 5


def test_platform_ai_endpoints_require_owner_or_admin_role(client):
    from app.models.enums import PlatformStaffRole
    from tests.test_platform_http import platform_login

    support_headers = platform_login(client, email="quota-support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    res = client.get("/api/v1/platform/ai/revenue-summary", headers=support_headers)
    assert res.status_code == 403
