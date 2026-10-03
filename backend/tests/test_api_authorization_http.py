"""BUILD-121: every endpoint requires a signed-in user, except a short, explicit
public list. Built from the OpenAPI schema, so a new route is covered the moment it
exists and a route added without auth fails this test instead of shipping."""

import re
import uuid

from app.main import app

PUBLIC = {
    ("GET", "/api/v1/health"),
    ("GET", "/api/v1/health/ready"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
}


def _operations() -> list[tuple[str, str]]:
    ops = []
    for path, methods in app.openapi()["paths"].items():
        for method in methods:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                ops.append((method.upper(), path))
    return sorted(ops)


OPERATIONS = _operations()


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)


def test_operation_list_is_not_empty():
    # Guards against the schema lookup silently returning nothing (e.g. after a FastAPI upgrade).
    assert len(OPERATIONS) > 80


def test_public_list_is_exactly_what_exists():
    assert PUBLIC <= set(OPERATIONS)


# One test per case (not parametrized): each test resets the database, and with ~120
# operations x 2 that alone added minutes to the suite. Failures list every offender.
def _unauthorized_offenders(client, headers: dict[str, str]) -> list[str]:
    offenders = []
    for method, path in OPERATIONS:
        if (method, path) in PUBLIC:
            continue
        res = client.request(method, _concrete(path), json={}, headers=headers)
        if res.status_code != 401:
            offenders.append(f"{method} {path} -> {res.status_code}")
    return offenders


def test_every_endpoint_rejects_requests_without_a_token(client):
    assert _unauthorized_offenders(client, {}) == []


def test_every_endpoint_rejects_a_forged_token(client):
    assert _unauthorized_offenders(client, {"Authorization": "Bearer not-a-real-token"}) == []


def test_refresh_token_cannot_be_used_as_an_access_token(client, auth_a):
    res = client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    refresh = res.json()["refresh_token"]
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert res.status_code == 401
