"""BUILD-142: request IDs, request logs and the readiness check."""

import logging


def test_every_response_has_a_request_id(client):
    res = client.get("/api/v1/health")
    assert len(res.headers["X-Request-ID"]) == 32
    assert client.get("/api/v1/health").headers["X-Request-ID"] != res.headers["X-Request-ID"]


def test_request_id_from_a_proxy_is_kept_if_sane(client):
    assert client.get("/api/v1/health", headers={"X-Request-ID": "lb-123"}).headers["X-Request-ID"] == "lb-123"
    long_id = "x" * 500
    assert client.get("/api/v1/health", headers={"X-Request-ID": long_id}).headers["X-Request-ID"] != long_id


def test_requests_are_logged_without_query_strings(client, auth_a, caplog):
    with caplog.at_level(logging.INFO, logger="buildos.request"):
        res = client.get("/api/v1/search?q=secret-term", headers=auth_a)
    line = next(r.getMessage() for r in caplog.records if r.name == "buildos.request")
    assert f"request_id={res.headers['X-Request-ID']}" in line
    assert "method=GET path=/api/v1/search status=200" in line
    assert "secret-term" not in line


def test_readiness_checks_the_database(client):
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 200 and res.json() == {"status": "ok", "database": "ok"}


def test_readiness_reports_a_dead_database(client):
    from app.db.session import get_db
    from app.main import app

    class DeadSession:
        def execute(self, *_):
            raise ConnectionError("db down")

    app.dependency_overrides[get_db] = lambda: DeadSession()
    try:
        res = client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.pop(get_db)
    assert res.status_code == 503 and res.json()["database"] == "unreachable"
