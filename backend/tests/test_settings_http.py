import pytest

from tests.conftest import make_user_in_company


def me(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()


# ---- Company settings (BUILD-103, 106) --------------------------------------


def test_admin_updates_company_settings(client, auth_a):
    res = client.patch("/api/v1/companies/me", headers=auth_a, json={
        "name": "Renamed Builders", "currency": "USD", "unit_system": "imperial", "phone": "+92 300 0000000",
    })
    assert res.status_code == 200, res.text
    company = client.get("/api/v1/companies/me", headers=auth_a).json()
    assert (company["name"], company["currency"], company["unit_system"]) == ("Renamed Builders", "USD", "imperial")


@pytest.mark.parametrize("body", [
    {"currency": "usd"},
    {"currency": "DOLLARS"},
    {"unit_system": "furlongs"},
    {"name": "X"},
    {"email": "not-an-email"},
])
def test_company_settings_validated(client, auth_a, body):
    res = client.patch("/api/v1/companies/me", headers=auth_a, json=body)
    assert res.status_code == 422, res.text


def test_non_admin_cannot_change_company(client, auth_a, viewer_a):
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    for headers in (viewer_a, pm):
        res = client.patch("/api/v1/companies/me", headers=headers, json={"currency": "USD"})
        assert res.status_code == 403
    assert client.get("/api/v1/companies/me", headers=viewer_a).json()["currency"] == "PKR"


def test_company_settings_are_per_company(client, auth_a, auth_b):
    client.patch("/api/v1/companies/me", headers=auth_a, json={"currency": "USD"})
    assert client.get("/api/v1/companies/me", headers=auth_b).json()["currency"] == "PKR"


# ---- User settings (BUILD-104) ----------------------------------------------


def test_update_own_name(client, auth_a):
    res = client.patch("/api/v1/auth/me", headers=auth_a, json={"full_name": "  New Name  "})
    assert res.status_code == 200
    assert me(client, auth_a)["full_name"] == "New Name"
    assert client.patch("/api/v1/auth/me", headers=auth_a, json={"full_name": ""}).status_code == 422


def test_own_profile_update_cannot_change_role(client, auth_a, viewer_a):
    res = client.patch("/api/v1/auth/me", headers=viewer_a, json={"full_name": "V", "role": "company_admin"})
    assert res.status_code == 200
    assert me(client, viewer_a)["role"] == "viewer"


def test_change_password(client, auth_a):
    res = client.post("/api/v1/auth/me/password", headers=auth_a,
                      json={"current_password": "password123", "new_password": "a-new-password"})
    assert res.status_code == 204
    login = lambda pw: client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": pw}).status_code
    assert login("password123") == 401
    assert login("a-new-password") == 200


def test_change_password_needs_current_password(client, auth_a):
    res = client.post("/api/v1/auth/me/password", headers=auth_a,
                      json={"current_password": "wrong-password", "new_password": "a-new-password"})
    assert res.status_code == 400
    res = client.post("/api/v1/auth/me/password", headers=auth_a,
                      json={"current_password": "password123", "new_password": "short"})
    assert res.status_code == 422
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"}).status_code == 200


# ---- Users and roles (BUILD-105) --------------------------------------------


def test_admin_lists_only_own_company_users(client, auth_a, auth_b, viewer_a):
    emails = [u["email"] for u in client.get("/api/v1/users", headers=auth_a).json()]
    assert sorted(emails) == ["a@example.com", "viewer@example.com"]
    assert "hashed_password" not in client.get("/api/v1/users", headers=auth_a).json()[0]


def test_non_admin_cannot_list_or_manage_users(client, auth_a, viewer_a):
    assert client.get("/api/v1/users", headers=viewer_a).status_code == 403
    admin_id = me(client, auth_a)["id"]
    assert client.patch(f"/api/v1/users/{admin_id}", headers=viewer_a, json={"role": "viewer"}).status_code == 403


def test_admin_changes_role(client, auth_a, viewer_a):
    viewer_id = me(client, viewer_a)["id"]
    res = client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"role": "site_engineer"})
    assert res.status_code == 200 and res.json()["role"] == "site_engineer"
    # The new role takes effect on the next request with the same token.
    assert me(client, viewer_a)["role"] == "site_engineer"


def test_deactivated_user_is_locked_out(client, auth_a, viewer_a):
    viewer_id = me(client, viewer_a)["id"]
    assert client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"is_active": False}).status_code == 200
    assert client.get("/api/v1/auth/me", headers=viewer_a).status_code == 401
    res = client.post("/api/v1/auth/login", json={"email": "viewer@example.com", "password": "password123"})
    assert res.status_code == 403


def test_admin_cannot_change_own_role_or_deactivate_self(client, auth_a):
    admin_id = me(client, auth_a)["id"]
    for body in ({"role": "viewer"}, {"is_active": False}):
        assert client.patch(f"/api/v1/users/{admin_id}", headers=auth_a, json=body).status_code == 400
    assert me(client, auth_a)["role"] == "company_admin"


def test_company_admin_cannot_grant_super_admin(client, auth_a, viewer_a):
    viewer_id = me(client, viewer_a)["id"]
    res = client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"role": "super_admin"})
    assert res.status_code == 403
    assert me(client, viewer_a)["role"] == "viewer"


def test_null_role_rejected(client, auth_a, viewer_a):
    viewer_id = me(client, viewer_a)["id"]
    assert client.patch(f"/api/v1/users/{viewer_id}", headers=auth_a, json={"role": None}).status_code == 422


def test_cannot_manage_another_companys_user(client, auth_a, auth_b):
    b_id = me(client, auth_b)["id"]
    res = client.patch(f"/api/v1/users/{b_id}", headers=auth_a, json={"is_active": False})
    assert res.status_code == 404
    assert client.get("/api/v1/auth/me", headers=auth_b).status_code == 200
