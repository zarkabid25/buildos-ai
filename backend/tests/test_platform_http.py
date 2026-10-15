"""Platform Super Admin (BUILD-143): a separate login for BuildOS's own staff,
who can see across every tenant company. The critical property is that a tenant
access token and a platform access token must never work on each other's routes."""

import uuid

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import PlatformStaffRole
from app.models.platform_admin import PlatformAdmin


def make_platform_admin(email: str = "admin@buildos.ai", password: str = "password123", role: PlatformStaffRole | None = None) -> None:
    with SessionLocal() as db:
        kwargs = {"role": role} if role is not None else {}
        db.add(PlatformAdmin(email=email, full_name="Platform Admin", hashed_password=hash_password(password), **kwargs))
        db.commit()


def platform_login(
    client, email: str = "admin@buildos.ai", password: str = "password123", role: PlatformStaffRole | None = None
) -> dict[str, str]:
    make_platform_admin(email, password, role)
    res = client.post("/api/v1/platform/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_login_rejects_wrong_password(client):
    make_platform_admin()
    res = client.post("/api/v1/platform/auth/login", json={"email": "admin@buildos.ai", "password": "wrong"})
    assert res.status_code == 401


def test_login_rejects_unknown_email(client):
    res = client.post("/api/v1/platform/auth/login", json={"email": "nobody@buildos.ai", "password": "x"})
    assert res.status_code == 401


def test_me_returns_the_admin(client):
    headers = platform_login(client)
    res = client.get("/api/v1/platform/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "admin@buildos.ai"


def test_disabled_platform_admin_cannot_log_in(client):
    make_platform_admin("disabled@buildos.ai", "password123")
    with SessionLocal() as db:
        admin = db.query(PlatformAdmin).filter(PlatformAdmin.email == "disabled@buildos.ai").first()
        admin.is_active = False
        db.commit()
    res = client.post(
        "/api/v1/platform/auth/login", json={"email": "disabled@buildos.ai", "password": "password123"}
    )
    assert res.status_code == 403


def test_a_tenant_access_token_cannot_reach_platform_routes(client, auth_a):
    res = client.get("/api/v1/platform/companies", headers=auth_a)
    assert res.status_code == 401


def test_a_platform_access_token_cannot_reach_tenant_routes(client, auth_a):
    platform_headers = platform_login(client)
    res = client.get("/api/v1/auth/me", headers=platform_headers)
    assert res.status_code == 401


def test_a_platform_refresh_token_cannot_be_used_as_a_platform_access_token(client):
    make_platform_admin()
    res = client.post("/api/v1/platform/auth/login", json={"email": "admin@buildos.ai", "password": "password123"})
    refresh_token = res.json()["refresh_token"]
    res = client.get("/api/v1/platform/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert res.status_code == 401


def test_platform_refresh_issues_a_new_working_access_token(client):
    make_platform_admin()
    res = client.post("/api/v1/platform/auth/login", json={"email": "admin@buildos.ai", "password": "password123"})
    refresh_token = res.json()["refresh_token"]
    res = client.post("/api/v1/platform/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    new_access = res.json()["access_token"]
    res = client.get("/api/v1/platform/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert res.status_code == 200


def test_list_companies_sees_every_tenant(client, auth_a, auth_b):
    headers = platform_login(client)
    res = client.get("/api/v1/platform/companies", headers=headers)
    assert res.status_code == 200
    codes = {c["code"] for c in res.json()["companies"]}
    assert {"AAA", "BBB"} <= codes


def test_user_count_reflects_real_users(client, auth_a, viewer_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]
    res = client.get(f"/api/v1/platform/companies/{company_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["user_count"] == 2


def test_suspending_a_company_blocks_its_users_from_logging_in(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    assert res.json()["suspended_at"] is not None

    res = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert res.status_code == 403


def test_suspending_a_company_invalidates_its_existing_sessions_too(client, auth_a):
    # Not just new logins: a token issued before the suspension must also stop working,
    # or a company banned mid-incident could keep acting until its token happened to expire.
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    res = client.get("/api/v1/auth/me", headers=auth_a)
    assert res.status_code == 200

    client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)

    res = client.get("/api/v1/auth/me", headers=auth_a)
    assert res.status_code == 401


def test_reactivating_a_company_restores_login(client, auth_a):
    headers = platform_login(client)
    company_id = client.get("/api/v1/auth/me", headers=auth_a).json()["company_id"]

    client.post(f"/api/v1/platform/companies/{company_id}/suspend", headers=headers)
    res = client.post(f"/api/v1/platform/companies/{company_id}/reactivate", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is True
    assert res.json()["suspended_at"] is None

    res = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert res.status_code == 200


def test_suspend_unknown_company_is_404(client):
    headers = platform_login(client)
    res = client.post(f"/api/v1/platform/companies/{uuid.uuid4()}/suspend", headers=headers)
    assert res.status_code == 404


def test_dashboard_counts_are_real(client, auth_a, auth_b):
    headers = platform_login(client)
    res = client.get("/api/v1/platform/dashboard", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["active_companies"] >= 2
    assert body["total_users"] >= 2
    # Not built yet: must stay null, never a fabricated number.
    assert body["monthly_recurring_revenue"] is None
    assert body["new_leads"] is None
    assert body["pending_supplier_verifications"] is None
