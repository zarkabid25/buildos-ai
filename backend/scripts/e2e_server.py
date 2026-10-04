"""Backend for the browser tests (frontend/e2e): a fresh, throwaway SQLite database
on every start, so tests never touch real data. Started by Playwright's webServer.

    python scripts/e2e_server.py  [port, default 8020]
"""

import os
import sys
import tempfile
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8020
FRONTEND = os.environ.get("E2E_FRONTEND_URL", "http://localhost:3020")

workdir = Path(tempfile.mkdtemp(prefix="buildos-e2e-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{workdir / 'e2e.db'}",
    STORAGE_DIR=str(workdir / "storage"),
    CORS_ORIGINS=f'["{FRONTEND}"]',
    ENVIRONMENT="test",
    LLM_API_KEY="",
    BCRYPT_ROUNDS="4",
    LOG_LEVEL="WARNING",  # keep per-request log lines out of the test output
    # Every test registers its own company from the same address.
    REGISTER_MAX_PER_IP="10000",
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import uvicorn  # noqa: E402

from app import models  # noqa: E402,F401
from app.db.base_class import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

Base.metadata.create_all(engine)
print(f"e2e backend: {workdir}", flush=True)
uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, log_level="warning")
