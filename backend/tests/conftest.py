import os
import tempfile

# Must be set before anything imports app.*: settings are cached and the
# SQLAlchemy engine is built at import time.
_tmp = tempfile.mkdtemp(prefix="buildos-tests-")
# SQLite by default (fast, no setup). Set TEST_DATABASE_URL to run the same suite
# against a real, *disposable* Postgres database, which catches Postgres-only
# behaviour. Every test drops and recreates all tables, so never point it at real data.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["MAX_UPLOAD_BYTES"] = str(1024 * 1024)
# An empty env var beats a key in backend/.env, so the suite can never hit the
# real Anthropic API even on a machine that has a key configured.
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_MODEL"] = "claude-opus-5"
os.environ["LLM_USE_FALLBACKS"] = "true"
os.environ["LLM_MAX_TOOL_ITERATIONS"] = "8"
# Minimum bcrypt cost: every test registers users, and at the production cost of 12
# each hash takes ~0.5s here. Same algorithm and hash format, just fewer rounds.
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import models  # noqa: E402,F401
from app.db.base_class import Base  # noqa: E402
from app.db.session import engine  # noqa: E402


# SQLite ignores foreign keys unless asked; Postgres always enforces them. Turn them
# on so a dangling reference fails here the same way it would in production.
@event.listens_for(engine, "connect")
def _enforce_foreign_keys(dbapi_connection, _record):
    if engine.dialect.name == "sqlite":
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


from app.main import app  # noqa: E402


# Build the schema once per run (drop first, in case a previous run was interrupted),
# then empty every table between tests: deleting rows takes milliseconds, whereas
# dropping and re-creating 40+ tables took about a second per test.
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


def _empty_all_tables() -> None:
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):  # children before parents (FKs on)
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def fresh_db():
    import shutil

    _empty_all_tables()
    # Uploaded files must not leak between tests either, or "nothing was stored"
    # assertions would depend on test order.
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)
    # Rate-limit counters are in memory and would otherwise carry over between tests.
    from app.core.rate_limit import limiter

    limiter.reset()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def register(client: TestClient, code: str, email: str) -> dict[str, str]:
    """Registers a company + admin through the real API and returns auth headers."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Company {code}",
            "company_code": code,
            "full_name": "Test Admin",
            "email": email,
            "password": "password123",
        },
    )
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def auth_a(client: TestClient) -> dict[str, str]:
    return register(client, "AAA", "a@example.com")


@pytest.fixture
def auth_b(client: TestClient) -> dict[str, str]:
    return register(client, "BBB", "b@example.com")


def make_user_in_company(client: TestClient, admin_headers: dict[str, str], email: str, role: str) -> dict[str, str]:
    """There's no invite flow yet, so create the extra user directly in the DB,
    then log in through the real API so the token path is still exercised."""
    import uuid

    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models.enums import UserRole
    from app.models.user import User

    company_id = uuid.UUID(client.get("/api/v1/auth/me", headers=admin_headers).json()["company_id"])
    with SessionLocal() as db:
        db.add(
            User(
                company_id=company_id,
                email=email,
                hashed_password=hash_password("password123"),
                full_name=f"{role} user",
                role=UserRole(role),
            )
        )
        db.commit()
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def viewer_a(client: TestClient, auth_a: dict[str, str]) -> dict[str, str]:
    return make_user_in_company(client, auth_a, "viewer@example.com", "viewer")
