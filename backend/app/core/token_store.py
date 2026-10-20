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
back to in-process memory when Redis was never configured/reachable in
the first place (development/test). Once Redis IS the backing store for a
process, though, a command that fails against an already-connected client
(Redis died mid-run) does NOT silently fall back to in-memory here -- see
RedisUnavailableError's docstring in redis_client.py for why this module
specifically chooses fail-closed over fail-open. rate_limit.py makes the
opposite choice deliberately; this isn't an oversight, it's two different
judgment calls for two different risk profiles.
"""

import time
from threading import Lock

import redis as redis_lib

from app.core.redis_client import RedisUnavailableError, get_redis, invalidate

_mem_revoked: dict[str, float] = {}  # jti -> expiry (monotonic-ish, using time.time())
_mem_versions: dict[str, int] = {}
_mem_lock = Lock()


def _redis_or_none():
    """Returns the cached client only if Redis was reachable when this
    process last checked. None means "never configured/reachable" (use the
    in-memory fallback, the normal dev/test path) -- a client that was
    reachable but then fails a command is handled separately, at each call
    site below, as a RedisUnavailableError rather than a silent fallback."""
    return get_redis()


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
    redis = _redis_or_none()
    if redis is not None:
        try:
            redis.set(f"revoked-jti:{jti}", "1", ex=ttl_seconds)
        except redis_lib.RedisError as exc:
            invalidate()
            raise RedisUnavailableError("Could not persist a token revocation -- Redis is unreachable.") from exc
        return
    with _mem_lock:
        _prune_mem()
        _mem_revoked[jti] = time.time() + ttl_seconds


def claim_jti(jti: str, ttl_seconds: float) -> bool:
    """Phase 10 (Task 1): atomically marks `jti` as used and returns True
    if THIS call is the first to claim it, False if it was already
    claimed/revoked. This is the single primitive that makes refresh-token
    rotation race-safe under concurrent requests for the same token --
    the previous check-then-set (`is_jti_revoked` then `revoke_jti`) had a
    window where two concurrent requests for the same refresh token could
    both see "not revoked yet" and both proceed, each minting a valid new
    session from what should have been a single-use token. Uses Redis's
    `SET ... NX` (set-if-not-exists), which is atomic server-side."""
    ttl_seconds = max(1, int(ttl_seconds))
    redis = _redis_or_none()
    if redis is not None:
        try:
            return bool(redis.set(f"revoked-jti:{jti}", "1", ex=ttl_seconds, nx=True))
        except redis_lib.RedisError as exc:
            invalidate()
            raise RedisUnavailableError("Could not atomically claim a refresh token -- Redis is unreachable.") from exc
    with _mem_lock:
        _prune_mem()
        if jti in _mem_revoked:
            return False
        _mem_revoked[jti] = time.time() + ttl_seconds
        return True


def is_jti_revoked(jti: str) -> bool:
    redis = _redis_or_none()
    if redis is not None:
        try:
            return bool(redis.exists(f"revoked-jti:{jti}"))
        except redis_lib.RedisError as exc:
            invalidate()
            raise RedisUnavailableError("Could not check token revocation status -- Redis is unreachable.") from exc
    with _mem_lock:
        _prune_mem()
        return jti in _mem_revoked


def get_session_version(key: str) -> int:
    redis = _redis_or_none()
    if redis is not None:
        try:
            value = redis.get(f"session-ver:{key}")
        except redis_lib.RedisError as exc:
            invalidate()
            raise RedisUnavailableError("Could not read session version -- Redis is unreachable.") from exc
        return int(value) if value is not None else 0
    with _mem_lock:
        return _mem_versions.get(key, 0)


def bump_session_version(key: str) -> int:
    """Returns the new version. Called on logout-all, suspension,
    deactivation, password change, and detected refresh-token reuse."""
    redis = _redis_or_none()
    if redis is not None:
        try:
            return int(redis.incr(f"session-ver:{key}"))
        except redis_lib.RedisError as exc:
            invalidate()
            raise RedisUnavailableError("Could not persist a session invalidation -- Redis is unreachable.") from exc
    with _mem_lock:
        _mem_versions[key] = _mem_versions.get(key, 0) + 1
        return _mem_versions[key]


def reset_for_tests() -> None:
    with _mem_lock:
        _mem_revoked.clear()
        _mem_versions.clear()
