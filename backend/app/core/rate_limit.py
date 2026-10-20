"""A small sliding-window limiter for the public auth endpoints (BUILD-125).

Phase 9.1 (Task 1): now backed by Redis when reachable (via
app.core.redis_client), using a sorted set per key so every worker/container
shares the same counts -- the single-process limitation from before this
phase only applies when Redis isn't configured or isn't reachable, in which
case this falls back to the original in-process behavior unchanged.
"""

import math
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException

from app.core.redis_client import get_redis


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _trim(self, key: str, window: float, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - window:
            events.popleft()
        return events

    def _redis_count(self, key: str, window: float, now: float) -> int:
        redis = get_redis()
        rkey = f"ratelimit:{key}"
        redis.zremrangebyscore(rkey, 0, now - window)
        return redis.zcard(rkey)

    def check(self, key: str, limit: int, window: float, message: str) -> None:
        """429 if `key` already has `limit` events inside the window."""
        redis = get_redis()
        if redis is not None:
            now = time.time()
            count = self._redis_count(key, window, now)
            if count >= limit:
                oldest = redis.zrange(f"ratelimit:{key}", 0, 0, withscores=True)
                retry_after = math.ceil(oldest[0][1] + window - now) if oldest else int(window)
                raise HTTPException(429, message, headers={"Retry-After": str(max(retry_after, 1))})
            return
        now = time.monotonic()
        with self._lock:
            events = self._trim(key, window, now)
            if len(events) >= limit:
                retry_after = math.ceil(events[0] + window - now)
                raise HTTPException(429, message, headers={"Retry-After": str(max(retry_after, 1))})

    def hit(self, key: str) -> None:
        redis = get_redis()
        if redis is not None:
            now = time.time()
            rkey = f"ratelimit:{key}"
            redis.zadd(rkey, {f"{now}:{uuid.uuid4()}": now})
            redis.expire(rkey, 3600)
            return
        with self._lock:
            self._events[key].append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        redis = get_redis()
        if redis is not None:
            if key is None:
                for rkey in redis.scan_iter("ratelimit:*"):
                    redis.delete(rkey)
            else:
                redis.delete(f"ratelimit:{key}")
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)


limiter = SlidingWindowLimiter()
