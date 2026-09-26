import os
import tempfile

# Must be set before anything imports app.*: settings are cached and the
# SQLAlchemy engine is built at import time.
_tmp = tempfile.mkdtemp(prefix="buildos-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["MAX_UPLOAD_BYTES"] = str(1024 * 1024)
# An empty env var beats a key in backend/.env, so the suite can never hit the
# real Anthropic API even on a machine that has a key configured.
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_MODEL"] = "claude-opus-5"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.db.base_class import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    import shutil

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    # Uploaded files must not leak between tests either, or "nothing was stored"
    # assertions would depend on test order.
    shutil.rmtree(os.environ["STORAGE_DIR"], ignore_errors=True)
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
