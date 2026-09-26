"""Drives requests through the real HTTP + JWT stack. Earlier verification called
service functions directly with real UUID objects and never exercised the
get_current_user path, which is how the JWT-string-vs-UUID bug shipped unnoticed."""

from tests.conftest import register


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/projects").status_code == 401


def test_me_works_with_valid_token(client, auth_a):
    res = client.get("/api/v1/auth/me", headers=auth_a)
    assert res.status_code == 200
    assert res.json()["email"] == "a@example.com"
    assert res.json()["role"] == "company_admin"


def test_garbage_token_is_401_not_500(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert res.status_code == 401


def test_refresh_token_cannot_be_used_as_access_token(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Company C",
            "company_code": "CCC",
            "full_name": "Test Admin",
            "email": "c@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    refresh = res.json()["refresh_token"]
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}).status_code == 401


def test_refresh_endpoint_issues_working_tokens(client):
    res = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Company C",
            "company_code": "DDD",
            "full_name": "Test Admin",
            "email": "d@example.com",
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": res.json()["refresh_token"]})
    assert refreshed.status_code == 200
    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_wrong_password_rejected(client, auth_a):
    res = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "nope-nope"})
    assert res.status_code == 401


def test_tenant_isolation_on_projects(client, auth_a, auth_b):
    created = client.post(
        "/api/v1/projects", headers=auth_a, json={"name": "Alpha Tower", "code": "ALPHA", "budget": "1000"}
    )
    assert created.status_code == 201
    project_id = created.json()["id"]

    assert client.get(f"/api/v1/projects/{project_id}", headers=auth_a).status_code == 200
    assert client.get(f"/api/v1/projects/{project_id}", headers=auth_b).status_code == 404
    assert client.get("/api/v1/projects", headers=auth_b).json() == []
