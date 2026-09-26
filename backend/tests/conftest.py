import os
import tempfile

# Must be set before anything imports app.*: settings are cached and the
# SQLAlchemy engine is built at import time.
_tmp = tempfile.mkdtemp(prefix="buildos-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["MAX_UPLOAD_BYTES"] = str(1024 * 1024)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.db.base_class import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
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
