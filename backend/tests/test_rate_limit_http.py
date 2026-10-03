"""BUILD-125: brute-force limits on the public auth endpoints."""

import time


def login(client, email="a@example.com", password="password123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_login_locks_after_five_failures(client, auth_a):
    for _ in range(5):
        assert login(client, password="wrong-password").status_code == 401
    res = login(client, password="wrong-password")
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) > 0
    # Locked means locked: even the right password is refused until the window passes,
    # otherwise the limit would just tell an attacker when they'd guessed right.
    assert login(client).status_code == 429


def test_success_clears_the_count(client, auth_a):
    for _ in range(4):
        login(client, password="wrong-password")
    assert login(client).status_code == 200
    for _ in range(4):
        assert login(client, password="wrong-password").status_code == 401
    assert login(client).status_code == 200


def test_lockout_is_per_account(client, auth_a, auth_b):
    for _ in range(5):
        login(client, password="wrong-password")
    assert login(client).status_code == 429
    assert login(client, email="b@example.com").status_code == 200


def test_email_case_doesnt_dodge_the_limit(client, auth_a):
    for i in range(5):
        login(client, email="A@Example.com" if i % 2 else "a@example.com", password="wrong-password")
    assert login(client).status_code == 429


def test_window_expires(client, auth_a, monkeypatch):
    for _ in range(5):
        login(client, password="wrong-password")
    assert login(client).status_code == 429
    real = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: real() + 15 * 60 + 1)
    assert login(client).status_code == 200


def test_register_is_capped_per_address(client):
    for i in range(10):
        res = client.post("/api/v1/auth/register", json={
            "company_name": f"Co {i}", "company_code": f"C{i:02d}", "full_name": "Admin",
            "email": f"admin{i}@example.com", "password": "password123",
        })
        assert res.status_code == 201, res.text
    res = client.post("/api/v1/auth/register", json={
        "company_name": "Co X", "company_code": "CXX", "full_name": "Admin",
        "email": "adminx@example.com", "password": "password123",
    })
    assert res.status_code == 429


def test_password_change_guessing_is_capped(client, auth_a):
    body = {"current_password": "wrong-password", "new_password": "a-new-password"}
    for _ in range(5):
        assert client.post("/api/v1/auth/me/password", headers=auth_a, json=body).status_code == 400
    right = {"current_password": "password123", "new_password": "a-new-password"}
    assert client.post("/api/v1/auth/me/password", headers=auth_a, json=right).status_code == 429
