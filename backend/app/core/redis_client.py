"""Phase 9.1/10: a single shared Redis client used by both the rate limiter
and the token-revocation store, so a multi-worker/multi-container deployment
finally shares state instead of each process keeping its own.

Development and tests: Redis is optional. If it's unreachable, `get_redis()`
returns None and every caller falls back to in-process memory (the same
single-process limitation documented in rate_limit.py and token_store.py).

Staging and production (Phase 10, Task 1): Redis is REQUIRED.
`verify_redis_at_startup()` is called once, at app creation, and raises if
Redis isn't reachable -- the process never starts serving traffic in a
silently-degraded state. If Redis goes away *after* a successful start
(network blip, Redis restart), calls don't hard-fail the request: each
call site in token_store.py/rate_limit.py catches `redis.RedisError`,
calls `invalidate()` here (so the next `get_redis()` re-probes instead of
reusing a dead connection), and falls back to in-process memory for that
one call -- but `/health/ready` is told the truth via `ping_fresh()`, so
the orchestrator/monitoring sees "not ready" even while the app keeps
serving degraded, single-process-correct responses rather than 503ing
every request over a transient Redis hiccup.
"""

import logging
import time
from threading import Lock

import redis as redis_lib

from app.core.config import Environment, Settings, get_settings

logger = logging.getLogger(__name__)


class RedisUnavailableError(RuntimeError):
    """Raised by token_store.py's security-critical paths (revocation
    checks and writes) when Redis was connected but a command against it
    just failed -- deliberately NOT swallowed into a silent in-memory
    fallback there, unlike rate_limit.py's deliberately fail-open choice.
    Losing rate limiting for a few seconds during a Redis blip is a minor
    availability cost; silently treating a revoked token as valid (or
    silently pretending a revocation was persisted when it wasn't) is a
    real security regression, so those paths fail closed instead and this
    exception is what they raise. app/api/deps.py turns it into a 503."""


_client: "redis_lib.Redis | None" = None
_checked = False
_last_probe_failed_at: float | None = None
# Avoid hammering a down Redis with a connection attempt on every single
# request; retry at most this often once we've seen it fail.
RECHECK_INTERVAL_SECONDS = 10.0
# Guards the check-then-connect sequence below -- without it, many threads
# racing to call get_redis() for the first time (e.g. 20 concurrent
# requests right after a cold start) could each independently attempt a
# connection instead of one winning and the rest reusing its result.
_connect_lock = Lock()


def _connect(url: str) -> "redis_lib.Redis":
    client = redis_lib.Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
    client.ping()
    return client


def get_redis() -> "redis_lib.Redis | None":
    """Cached for performance: a live client is reused across calls without
    re-pinging every time. On the failure path, re-probes at most once per
    RECHECK_INTERVAL_SECONDS, so a Redis that comes back up is picked up
    again automatically within that window instead of staying "down"
    forever for the life of the process (the pre-Phase-10 behavior)."""
    global _client, _checked, _last_probe_failed_at
    if _checked and _client is not None:
        return _client
    now = time.monotonic()
    if _checked and _last_probe_failed_at is not None and (now - _last_probe_failed_at) < RECHECK_INTERVAL_SECONDS:
        return None
    with _connect_lock:
        # Re-check inside the lock: another thread may have already
        # connected (or already recorded a fresh failure) while this one
        # was waiting for the lock.
        if _checked and _client is not None:
            return _client
        now = time.monotonic()
        if _checked and _last_probe_failed_at is not None and (now - _last_probe_failed_at) < RECHECK_INTERVAL_SECONDS:
            return None
        _checked = True
        try:
            _client = _connect(get_settings().redis_url)
            _last_probe_failed_at = None
        except Exception:
            logger.warning("Redis not reachable -- falling back to in-process state (single worker only).")
            _client = None
            _last_probe_failed_at = now
        return _client


def invalidate() -> None:
    """Called by a caller whose command against the cached client just
    failed (connection dropped, Redis restarted mid-connection, etc.) --
    forces the next get_redis() to re-probe rather than keep handing out a
    dead connection object."""
    global _client, _checked
    _client = None
    _checked = False


def ping_fresh(timeout: float = 0.5) -> bool:
    """An always-live check, never using the cache above -- for health
    endpoints and the startup check, where a stale "it was reachable 10
    minutes ago" answer would be actively misleading."""
    try:
        client = redis_lib.Redis.from_url(get_settings().redis_url, socket_connect_timeout=timeout, socket_timeout=timeout)
        return bool(client.ping())
    except Exception:
        return False


def verify_redis_at_startup(settings: Settings | None = None) -> None:
    """Phase 10, Task 1: "require Redis in staging and production; fail
    startup... when Redis is unavailable." Called once from
    app.main.create_app(). Development and test are unaffected -- Redis
    stays optional there, matching every test run of this project so far,
    none of which has ever had a real Redis available."""
    settings = settings or get_settings()
    if settings.environment not in (Environment.STAGING, Environment.PRODUCTION):
        return
    if not ping_fresh():
        raise RuntimeError(
            f"Redis is required in {settings.environment.value} (REDIS_URL={settings.redis_url}) but is not reachable. "
            "Refusing to start: rate limiting and session revocation would otherwise silently run in "
            "single-process-only mode, which is unsafe with more than one backend worker/container."
        )


def reset_for_tests() -> None:
    """Test-only: forces the next get_redis()/verify_redis_at_startup() call
    to re-check, since tests run with no Redis server and must not cache a
    stale result across unrelated test modules that patch settings.redis_url."""
    global _client, _checked, _last_probe_failed_at
    _client = None
    _checked = False
    _last_probe_failed_at = None
