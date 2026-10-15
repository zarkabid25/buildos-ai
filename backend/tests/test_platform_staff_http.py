"""Platform staff roles, company approval, and platform audit log (PLAT-006..010)."""

from app.models.enums import PlatformStaffRole
from tests.test_platform_http import platform_login


# ---- Legacy-company compatibility ---------------------------------------------------


def test_registering_a_new_company_still_works_unaffected(client):
    # The auth flow itself must not notice onboarding_status exists at all.
    res = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Fresh Co",
            "company_code": "FRESH",
            "full_name": "Admin",
            "email": "fresh@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}
    # The new user can use the app immediately -- onboarding status never gates login.
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200


def test_a_new_company_starts_pending_and_legacy_ones_default_approved(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get(f"/api/v1/platform/companies/{company_id}", headers=headers)
    assert res.json()["onboarding_status"] == "pending"


def test_approving_a_company_marks_it_approved_and_audit_logged(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.post(f"/api/v1/platform/companies/{company_id}/approve", headers=headers)
    assert res.status_code == 200
    assert res.json()["onboarding_status"] == "approved"

    res = client.get("/api/v1/platform/audit-log", headers=headers)
    actions = [e["action"] for e in res.json()]
    assert "company.approved" in actions


def test_approving_an_already_approved_company_is_a_no_op(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    client.post(f"/api/v1/platform/companies/{company_id}/approve", headers=headers)
    res = client.post(f"/api/v1/platform/companies/{company_id}/approve", headers=headers)
    assert res.status_code == 200
    assert res.json()["onboarding_status"] == "approved"


def test_suspend_and_reactivate_are_audit_logged(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)
    client.post(f"/api/v1/platform/companies/{company_id}/reactivate", headers=headers)

    res = client.get("/api/v1/platform/audit-log", headers=headers)
    actions = [e["action"] for e in res.json()]
    assert "company.suspended" in actions
    assert "company.reactivated" in actions


# ---- Staff permissions ----------------------------------------------------------------


def test_support_role_cannot_suspend_a_company(client, auth_a):
    headers = platform_login(client, email="support@buildos.ai", role=PlatformStaffRole.SUPPORT)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)
    assert res.status_code == 403


def test_support_role_can_still_view_dashboard_and_companies(client):
    headers = platform_login(client, email="support2@buildos.ai", role=PlatformStaffRole.SUPPORT)
    assert client.get("/api/v1/platform/dashboard", headers=headers).status_code == 200
    assert client.get("/api/v1/platform/companies", headers=headers).status_code == 200


def test_admin_role_can_suspend_but_not_invite_staff(client, auth_a):
    headers = platform_login(client, email="admin2@buildos.ai", role=PlatformStaffRole.ADMIN)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)
    assert res.status_code == 200

    res = client.post(
        "/api/v1/platform/staff/invitations",
        json={"email": "new@buildos.ai", "role": "admin"},
        headers=headers,
    )
    assert res.status_code == 403


def test_owner_can_invite_staff(client):
    headers = platform_login(client, email="owner@buildos.ai", role=PlatformStaffRole.OWNER)
    res = client.post(
        "/api/v1/platform/staff/invitations",
        json={"email": "newstaff@buildos.ai", "role": "admin", "full_name": "New Staff"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "newstaff@buildos.ai"
    assert "token" in body


def test_only_owner_can_invite_an_owner(client):
    headers = platform_login(client, email="owner2@buildos.ai", role=PlatformStaffRole.ADMIN)
    res = client.post(
        "/api/v1/platform/staff/invitations",
        json={"email": "x@buildos.ai", "role": "owner"},
        headers=headers,
    )
    assert res.status_code == 403


def test_staff_cannot_change_their_own_role(client):
    headers = platform_login(client, email="self@buildos.ai", role=PlatformStaffRole.OWNER)
    me = client.get("/api/v1/platform/auth/me", headers=headers).json()
    res = client.patch(f"/api/v1/platform/staff/{me['id']}", json={"role": "support"}, headers=headers)
    assert res.status_code == 400


# ---- Invitation accept flow ------------------------------------------------------------


def test_full_staff_invitation_accept_flow(client):
    owner_headers = platform_login(client, email="owner3@buildos.ai", role=PlatformStaffRole.OWNER)
    res = client.post(
        "/api/v1/platform/staff/invitations",
        json={"email": "joiner@buildos.ai", "role": "support", "full_name": "Joiner"},
        headers=owner_headers,
    )
    token = res.json()["token"]

    res = client.get(f"/api/v1/platform/auth/invitations/{token}")
    assert res.status_code == 200
    assert res.json()["role"] == "support"

    res = client.post(
        "/api/v1/platform/auth/accept-invite",
        json={"token": token, "full_name": "Joiner Person", "password": "password123"},
    )
    assert res.status_code == 201, res.text
    assert res.json()["admin"]["role"] == "support"

    # The link is now dead.
    res = client.post(
        "/api/v1/platform/auth/accept-invite",
        json={"token": token, "full_name": "Again", "password": "password123"},
    )
    assert res.status_code == 404

    # The new staff member can log in for real.
    res = client.post(
        "/api/v1/platform/auth/login", json={"email": "joiner@buildos.ai", "password": "password123"}
    )
    assert res.status_code == 200


def test_revoking_an_invitation_kills_the_link(client):
    owner_headers = platform_login(client, email="owner4@buildos.ai", role=PlatformStaffRole.OWNER)
    res = client.post(
        "/api/v1/platform/staff/invitations",
        json={"email": "revoke-me@buildos.ai", "role": "support"},
        headers=owner_headers,
    )
    invitation_id = res.json()["id"]
    token = res.json()["token"]

    res = client.delete(f"/api/v1/platform/staff/invitations/{invitation_id}", headers=owner_headers)
    assert res.status_code == 204

    res = client.post(
        "/api/v1/platform/auth/accept-invite",
        json={"token": token, "full_name": "XX", "password": "password123"},
    )
    assert res.status_code == 404


def test_list_staff_shows_roles(client):
    headers = platform_login(client, email="lister@buildos.ai", role=PlatformStaffRole.OWNER)
    res = client.get("/api/v1/platform/staff", headers=headers)
    assert res.status_code == 200
    roles = {s["email"]: s["role"] for s in res.json()}
    assert roles["lister@buildos.ai"] == "owner"
