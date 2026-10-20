"""A small sliding-window limiter for the public auth endpoints (BUILD-125).

Phase 9.1 (Task 1): now backed by Redis when reachable (via
app.core.redis_client), using a sorted set per key so every worker/container
shares the same counts -- the single-process limitation from before this
phase only applies when Redis isn't configured or isn't reachable, in which
case this falls back to the original in-process behavior unchanged.

Phase 10 (Task 1): if a Redis command fails against an already-connected
client (Redis died mid-run), this module deliberately FAILS OPEN -- logs a
warning, invalidates the cached client so the next call re-probes, and
falls back to the in-process limiter for that one call -- rather than
raising and blocking every login/request. Losing rate-limit coverage for a
few seconds during a Redis blip is a minor, acceptable cost; refusing every
login because the rate limiter couldn't reach Redis would be worse. This is
the opposite judgment call from token_store.py's revocation checks, which
fail closed -- see RedisUnavailableError's docstring for why.
"""

import logging
import math
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

import redis as redis_lib
from fastapi import HTTPException

from app.core.redis_client import get_redis, invalidate

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _trim(self, key: str, window: float, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - window:
            events.popleft()
        return events

    def _redis_fail_open(self, exc: Exception) -> None:
        logger.warning("Redis command failed in rate limiter -- failing open for this call: %s", exc)
        invalidate()

    def check(self, key: str, limit: int, window: float, message: str) -> None:
        """429 if `key` already has `limit` events inside the window."""
        redis = get_redis()
        if redis is not None:
            try:
                now = time.time()
                rkey = f"ratelimit:{key}"
                redis.zremrangebyscore(rkey, 0, now - window)
                count = redis.zcard(rkey)
                if count >= limit:
                    oldest = redis.zrange(rkey, 0, 0, withscores=True)
                    retry_after = math.ceil(oldest[0][1] + window - now) if oldest else int(window)
                    raise HTTPException(429, message, headers={"Retry-After": str(max(retry_after, 1))})
                return
            except redis_lib.RedisError as exc:
                self._redis_fail_open(exc)
        now = time.monotonic()
        with self._lock:
            events = self._trim(key, window, now)
            if len(events) >= limit:
                retry_after = math.ceil(events[0] + window - now)
                raise HTTPException(429, message, headers={"Retry-After": str(max(retry_after, 1))})

    def hit(self, key: str) -> None:
        redis = get_redis()
        if redis is not None:
            try:
                now = time.time()
                rkey = f"ratelimit:{key}"
                redis.zadd(rkey, {f"{now}:{uuid.uuid4()}": now})
                redis.expire(rkey, 3600)
                return
            except redis_lib.RedisError as exc:
                self._redis_fail_open(exc)
        with self._lock:
            self._events[key].append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        redis = get_redis()
        if redis is not None:
            try:
                if key is None:
                    for rkey in redis.scan_iter("ratelimit:*"):
                        redis.delete(rkey)
                else:
                    redis.delete(f"ratelimit:{key}")
            except redis_lib.RedisError as exc:
                self._redis_fail_open(exc)
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)


limiter = SlidingWindowLimiter()
