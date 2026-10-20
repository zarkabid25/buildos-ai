"""Phase 9.1: a single shared, lazily-connected Redis client used by both the
rate limiter and the token-revocation store, so a multi-worker/multi-container
deployment finally shares state instead of each process keeping its own.

Every caller must treat Redis as optional: if it's unreachable (not
configured, not running, wrong URL -- the common case in tests and on a
single dev machine with nothing extra started), every function here returns
None/raises nothing, and the caller falls back to in-process memory. That
fallback has the exact same single-process limitation documented in
rate_limit.py and token_store.py -- this module only removes that limitation
when Redis is actually reachable, it never requires it.
"""

import logging

import redis as redis_lib

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: "redis_lib.Redis | None" = None
_checked = False


def get_redis() -> "redis_lib.Redis | None":
    global _client, _checked
    if _checked:
        return _client
    _checked = True
    try:
        client = redis_lib.Redis.from_url(get_settings().redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.ping()
        _client = client
    except Exception:
        logger.warning("Redis not reachable at startup -- falling back to in-process state (single worker only).")
        _client = None
    return _client


def reset_for_tests() -> None:
    """Test-only: forces the next get_redis() call to re-check, since tests
    run with no Redis server and must not cache a stale "unreachable" result
    across unrelated test modules that patch settings.redis_url."""
    global _client, _checked
    _client = None
    _checked = False
