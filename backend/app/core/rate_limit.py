"""A small sliding-window limiter for the public auth endpoints (BUILD-125).

State lives in this process's memory: it protects a single-process deployment
(the current Docker setup runs one uvicorn worker) but each extra worker or
container would count separately. Redis is already in docker-compose for when that
matters; swapping it in means reimplementing these three methods, not the callers.
"""

import math
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _trim(self, key: str, window: float, now: float) -> deque[float]:
        events = self._events[key]
        while events and events[0] <= now - window:
            events.popleft()
        return events

    def check(self, key: str, limit: int, window: float, message: str) -> None:
        """429 if `key` already has `limit` events inside the window."""
        now = time.monotonic()
        with self._lock:
            events = self._trim(key, window, now)
            if len(events) >= limit:
                retry_after = math.ceil(events[0] + window - now)
                raise HTTPException(429, message, headers={"Retry-After": str(max(retry_after, 1))})

    def hit(self, key: str) -> None:
        with self._lock:
            self._events[key].append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)


limiter = SlidingWindowLimiter()
