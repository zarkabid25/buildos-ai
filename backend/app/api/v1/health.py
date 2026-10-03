from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness: the process is up. Deliberately touches nothing else."""
    return {"status": "ok", "service": "buildos-ai-backend"}


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness: the app can actually serve requests, i.e. the database answers.
    For load balancers / orchestrators; returns 503 rather than hanging or crashing."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "unreachable"})
    return {"status": "ok", "database": "ok"}
