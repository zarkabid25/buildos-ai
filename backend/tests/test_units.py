"""BUILD-127: unit tests for pure logic, without going through HTTP. The HTTP suites
cover the same rules end to end; these pin down edge cases cheaply."""

import io
import zipfile
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.rate_limit import SlidingWindowLimiter
from app.core.storage import content_matches_type
from app.db.updates import apply_changes
from app.models.warehouse import Warehouse
from app.services.project_service import get_schedule_variance_days, get_schedule_variance_percent


def project(start, end, progress=0):
    return SimpleNamespace(start_date=start, end_date=end, progress_percent=progress)


# ---- Schedule variance -------------------------------------------------------------


@pytest.mark.parametrize("today,progress,expected_percent,expected_days", [
    (date(2026, 1, 1), 0, 0, 0),        # first day, nothing expected yet
    (date(2026, 2, 20), 20, 30, 30),    # day 50 of 100, 20% done -> 30 behind
    (date(2026, 2, 20), 80, -30, -30),  # ahead of schedule is negative
    (date(2026, 6, 1), 90, 10, 10),     # past the end date: elapsed is capped at 100%
])
def test_schedule_variance(today, progress, expected_percent, expected_days):
    p = project(date(2026, 1, 1), date(2026, 4, 11), progress)  # 100-day project
    assert get_schedule_variance_percent(p, today) == expected_percent
    assert get_schedule_variance_days(p, today) == expected_days


@pytest.mark.parametrize("start,end,today", [
    (None, date(2026, 4, 1), date(2026, 2, 1)),            # no start date
    (date(2026, 1, 1), None, date(2026, 2, 1)),            # no end date
    (date(2026, 1, 1), date(2026, 1, 1), date(2026, 1, 1)),  # zero-length project
    (date(2026, 3, 1), date(2026, 4, 1), date(2026, 2, 1)),  # hasn't started yet
])
def test_schedule_variance_needs_a_running_schedule(start, end, today):
    assert get_schedule_variance_percent(project(start, end), today) is None
    assert get_schedule_variance_days(project(start, end), today) is None


# ---- Upload content check -------------------------------------------------------------


def office_package(member: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(member, "<x/>")
    return buf.getvalue()


DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@pytest.mark.parametrize("content_type,content,ok", [
    ("application/pdf", b"%PDF-1.7\n...", True),
    ("application/pdf", b"MZ\x90\x00", False),
    ("image/png", b"\x89PNG\r\n\x1a\n....", True),
    ("image/png", b"\xff\xd8\xff\xe0", False),  # a JPEG claiming to be PNG
    ("image/jpeg", b"\xff\xd8\xff\xe0", True),
    ("image/webp", b"RIFF\x00\x00\x00\x00WEBPVP8 ", True),
    ("image/webp", b"RIFF\x00\x00\x00\x00WAVEfmt ", False),  # a WAV file
    (DOCX, office_package("word/document.xml"), True),
    (DOCX, office_package("xl/workbook.xml"), False),  # a spreadsheet named .docx
    (XLSX, office_package("xl/workbook.xml"), True),
    (XLSX, b"not a zip at all", False),
    ("application/msword", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 8, True),
    ("text/csv", "a,b\nCafé,1\n".encode("cp1252"), True),
    ("text/csv", b"a,b\n\x00\x01", False),
    ("application/x-msdownload", b"MZ", False),  # not an allowed type at all
])
def test_content_matches_type(content_type, content, ok):
    assert content_matches_type(content_type, content) is ok


# ---- Rate limiter ---------------------------------------------------------------------


def test_limiter_blocks_at_the_limit_and_reports_retry_after(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("app.core.rate_limit.time.monotonic", lambda: now[0])
    limiter = SlidingWindowLimiter()
    for _ in range(3):
        limiter.check("k", 3, 60, "slow down")
        limiter.hit("k")
        now[0] += 10
    with pytest.raises(HTTPException) as exc:
        limiter.check("k", 3, 60, "slow down")
    assert exc.value.status_code == 429
    assert exc.value.headers["Retry-After"] == "30"  # oldest hit (t=1000) leaves the window at t=1060; now is 1030
    now[0] += 30
    limiter.check("k", 3, 60, "slow down")  # oldest hit has expired


def test_limiter_keys_are_independent_and_resettable():
    limiter = SlidingWindowLimiter()
    limiter.hit("a")
    limiter.check("b", 1, 60, "x")
    with pytest.raises(HTTPException):
        limiter.check("a", 1, 60, "x")
    limiter.reset("a")
    limiter.check("a", 1, 60, "x")


# ---- apply_changes --------------------------------------------------------------------


def test_apply_changes_rejects_null_only_for_required_columns():
    wh = Warehouse(name="Main", location="Yard 1")
    apply_changes(wh, {"location": None})
    assert wh.location is None
    with pytest.raises(HTTPException) as exc:
        apply_changes(wh, {"name": None})
    assert exc.value.status_code == 422
    assert wh.name == "Main"


def test_test_database_enforces_foreign_keys():
    """conftest turns this on so SQLite behaves like Postgres; guard against it silently not applying."""
    from sqlalchemy import text

    from app.db.session import engine

    if engine.dialect.name != "sqlite":
        pytest.skip("only SQLite needs foreign keys switched on")
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1


# ---- Production config guard (BUILD-137) ------------------------------------------------


SAFE_PRODUCTION = {
    "environment": "production",
    "jwt_secret_key": "x" * 40,
    "database_url": "postgresql://app:s3cret@db.internal:5432/buildos",
    "cors_origins": ["https://app.example.com"],
    "bcrypt_rounds": 12,
}


def test_safe_production_config_starts():
    from app.core.config import Settings

    Settings(_env_file=None, **SAFE_PRODUCTION)


@pytest.mark.parametrize("override,message", [
    ({"jwt_secret_key": "change-me-in-production"}, "JWT_SECRET_KEY"),
    ({"jwt_secret_key": "short"}, "JWT_SECRET_KEY"),
    ({"database_url": "postgresql://buildos:buildos@db:5432/buildos"}, "DATABASE_URL"),
    ({"cors_origins": ["http://localhost:3000"]}, "CORS_ORIGINS"),
    ({"bcrypt_rounds": 4}, "BCRYPT_ROUNDS"),
])
def test_unsafe_production_config_refuses_to_start(override, message):
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match=message):
        Settings(_env_file=None, **{**SAFE_PRODUCTION, **override})


def test_development_defaults_still_allowed():
    from app.core.config import Settings

    Settings(_env_file=None, environment="development")
