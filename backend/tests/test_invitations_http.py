"""BUILD-105: inviting people into the company with a role."""

from datetime import datetime, timedelta, timezone

from tests.conftest import make_user_in_company


def invite(client, headers, email="new@example.com", role="site_engineer", **extra):
    return client.post("/api/v1/users/invitations", headers=headers, json={"email": email, "role": role, **extra})


def accept(client, token, name="New Person", password="a-good-password"):
    return client.post("/api/v1/auth/accept-invite", json={"token": token, "full_name": name, "password": password})


def test_invite_and_accept_joins_the_company_with_that_role(client, auth_a):
    res = invite(client, auth_a, email="New@Example.com", full_name="Nadia")
    assert res.status_code == 201
    inv = res.json()
    assert (inv["email"], inv["role"], inv["invited_by_name"], inv["expired"]) == ("new@example.com", "site_engineer", "Test Admin", False)
    token = inv["token"]

    # The person opening the link sees which company and role before accepting.
    info = client.get(f"/api/v1/auth/invitations/{token}").json()
    assert info == {"company_name": "Company AAA", "email": "new@example.com", "full_name": "Nadia", "role": "site_engineer"}

    res = accept(client, token)
    assert res.status_code == 201
    body = res.json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}).json()
    admin = client.get("/api/v1/auth/me", headers=auth_a).json()
    assert (me["role"], me["company_id"], me["full_name"]) == ("site_engineer", admin["company_id"], "New Person")

    # Login works, case-insensitively, and the link can't be reused.
    login = client.post("/api/v1/auth/login", json={"email": "NEW@example.com", "password": "a-good-password"})
    assert login.status_code == 200
    assert accept(client, token).status_code == 404
    assert client.get("/api/v1/users/invitations", headers=auth_a).json() == []
    actions = [e["action"] for e in client.get("/api/v1/audit-log", headers=auth_a).json()]
    assert "user.invited" in actions and "user.joined" in actions


def test_token_is_shown_once_and_stored_hashed(client, auth_a):
    token = invite(client, auth_a).json()["token"]
    [listed] = client.get("/api/v1/users/invitations", headers=auth_a).json()
    assert "token" not in listed
    from app.db.session import SessionLocal
    from app.models.invitation import Invitation

    with SessionLocal() as db:
        stored = db.query(Invitation).one()
        assert stored.token_hash != token and len(stored.token_hash) == 64


def test_bad_expired_and_revoked_links(client, auth_a):
    assert client.get("/api/v1/auth/invitations/" + "x" * 43).status_code == 404
    inv = invite(client, auth_a).json()

    from app.db.session import SessionLocal
    from app.models.invitation import Invitation

    with SessionLocal() as db:
        row = db.get(Invitation, __import__("uuid").UUID(inv["id"]))
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    assert client.get(f"/api/v1/auth/invitations/{inv['token']}").status_code == 410
    assert accept(client, inv["token"]).status_code == 410
    assert client.get("/api/v1/users/invitations", headers=auth_a).json()[0]["expired"] is True

    second = invite(client, auth_a, email="other@example.com").json()
    assert client.delete(f"/api/v1/users/invitations/{second['id']}", headers=auth_a).status_code == 204
    assert accept(client, second["token"]).status_code == 404


def test_reinviting_replaces_the_old_link(client, auth_a):
    first = invite(client, auth_a).json()
    second = invite(client, auth_a, role="accountant").json()
    assert accept(client, first["token"]).status_code == 404
    assert accept(client, second["token"]).status_code == 201
    assert client.post("/api/v1/auth/login", json={"email": "new@example.com", "password": "a-good-password"}).status_code == 200


def test_cannot_invite_an_existing_account(client, auth_a, auth_b):
    assert invite(client, auth_a, email="b@example.com").status_code == 409  # already in another company
    assert invite(client, auth_a, email="A@EXAMPLE.COM").status_code == 409


def test_only_admins_invite_and_only_super_admins_invite_super_admins(client, auth_a, viewer_a):
    assert invite(client, viewer_a).status_code == 403
    pm = make_user_in_company(client, auth_a, "pm@example.com", "project_manager")
    assert invite(client, pm).status_code == 403
    assert client.get("/api/v1/users/invitations", headers=pm).status_code == 403
    assert invite(client, auth_a, role="super_admin").status_code == 403


def test_invitations_are_per_company(client, auth_a, auth_b):
    inv = invite(client, auth_a).json()
    assert client.get("/api/v1/users/invitations", headers=auth_b).json() == []
    assert client.delete(f"/api/v1/users/invitations/{inv['id']}", headers=auth_b).status_code == 404
    assert accept(client, inv["token"]).status_code == 201  # still valid: B couldn't revoke it


def test_accept_validates_input(client, auth_a):
    token = invite(client, auth_a).json()["token"]
    assert accept(client, token, password="short").status_code == 422
    assert accept(client, token, name="").status_code == 422
    assert accept(client, token).status_code == 201
