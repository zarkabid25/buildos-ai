from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Environment, get_settings
from app.core.redis_client import ping_fresh
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness: the process is up. Deliberately touches nothing else."""
    return {"status": "ok", "service": "buildos-ai-backend"}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness: the app can actually serve requests. For load balancers /
    orchestrators; returns 503 rather than hanging or crashing.

    Phase 10 (Task 1): also reports real Redis status, always using a fresh
    (uncached) probe -- the app itself keeps serving degraded, single-
    process-correct responses if Redis drops mid-run (see rate_limit.py /
    token_store.py), but readiness must tell the truth so an orchestrator or
    on-call engineer finds out. In staging/production, where Redis is
    required, an unreachable Redis makes this endpoint unready (503) even
    though the process is technically still handling requests -- that's the
    point: it should get restarted or alerted on, not quietly tolerated."""
    settings = get_settings()
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    redis_ok = ping_fresh(timeout=0.3)
    redis_required = settings.environment in (Environment.STAGING, Environment.PRODUCTION)

    body = {
        "status": "ok" if db_ok and (redis_ok or not redis_required) else "unavailable",
        "database": "ok" if db_ok else "unreachable",
        "redis": "ok" if redis_ok else ("unreachable" if redis_required else "unreachable (optional in this environment)"),
    }
    status_code = 200 if body["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=body)
