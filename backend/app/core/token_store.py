"""Phase 9.1 (Task 1): server-side token revocation and session invalidation.

Two independent mechanisms, both keyed off the `jti`/`sv` claims security.py
puts on every token:

1. A per-token denylist (`revoke_jti`/`is_jti_revoked`) for: logging out one
   specific session, and refusing a refresh token that's already been
   rotated away (reuse detection -- see auth_service.refresh and its two
   siblings).
2. A per-subject "session version" counter (`get_session_version`/
   `bump_session_version`). Every token is minted carrying the subject's
   version *at issue time* (claim "sv"); `deps.py` compares that against the
   current version on every request. Bumping it immediately invalidates
   every token for that subject -- used for logout-all-sessions, account
   suspension/deactivation, password changes, and as the blanket response to
   a detected refresh-token-reuse attack.

Backed by Redis when reachable (shared across workers/containers); falls
back to in-process memory otherwise, with the same single-process caveat
already documented on rate_limit.py. Either way, callers never see the
difference.
"""

import time
from threading import Lock

from app.core.redis_client import get_redis

_mem_revoked: dict[str, float] = {}  # jti -> expiry (monotonic-ish, using time.time())
_mem_versions: dict[str, int] = {}
_mem_lock = Lock()


def _prune_mem() -> None:
    now = time.time()
    expired = [k for k, exp in _mem_revoked.items() if exp <= now]
    for k in expired:
        _mem_revoked.pop(k, None)


def revoke_jti(jti: str, ttl_seconds: float) -> None:
    """ttl_seconds should be the token's remaining lifetime -- no need to
    remember a revocation past the point the token would have expired
    anyway."""
    ttl_seconds = max(1, int(ttl_seconds))
    redis = get_redis()
    if redis is not None:
        redis.set(f"revoked-jti:{jti}", "1", ex=ttl_seconds)
        return
    with _mem_lock:
        _prune_mem()
        _mem_revoked[jti] = time.time() + ttl_seconds


def is_jti_revoked(jti: str) -> bool:
    redis = get_redis()
    if redis is not None:
        return bool(redis.exists(f"revoked-jti:{jti}"))
    with _mem_lock:
        _prune_mem()
        return jti in _mem_revoked


def get_session_version(key: str) -> int:
    redis = get_redis()
    if redis is not None:
        value = redis.get(f"session-ver:{key}")
        return int(value) if value is not None else 0
    with _mem_lock:
        return _mem_versions.get(key, 0)


def bump_session_version(key: str) -> int:
    """Returns the new version. Called on logout-all, suspension,
    deactivation, password change, and detected refresh-token reuse."""
    redis = get_redis()
    if redis is not None:
        return int(redis.incr(f"session-ver:{key}"))
    with _mem_lock:
        _mem_versions[key] = _mem_versions.get(key, 0) + 1
        return _mem_versions[key]


def reset_for_tests() -> None:
    with _mem_lock:
        _mem_revoked.clear()
        _mem_versions.clear()
