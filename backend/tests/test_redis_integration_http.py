"""Phase 10 (Task 1): integration tests against a real Redis-protocol TCP
server (fakeredis's `TcpFakeServer`) -- not the in-process fallback this
project has relied on in every prior test run, and not a real managed
Redis (none has ever been reachable from this project). This is the
closest honest substitute available on a machine with no Redis installed:
a real server, real sockets, real `redis.Redis` client connections (one
per "worker" below), exercising the actual Redis commands token_store.py
and rate_limit.py send -- not a mock of the Python code itself."""

import threading
import time

import pytest
import redis as redis_lib
from fakeredis import TcpFakeServer

from app.core import redis_client as redis_client_module
from app.core.config import Environment, get_settings
from app.core.redis_client import verify_redis_at_startup
from app.core.token_store import bump_session_version, claim_jti, get_session_version, is_jti_revoked, revoke_jti


def _free_port() -> int:
    import socket as _socket

    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake_redis_server():
    port = _free_port()
    server = TcpFakeServer(("127.0.0.1", port), server_type="redis")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        # give the listener a moment to actually bind before tests connect
        for _ in range(50):
            try:
                redis_lib.Redis(host="127.0.0.1", port=port, socket_connect_timeout=0.2).ping()
                break
            except Exception:
                time.sleep(0.05)
        yield f"redis://127.0.0.1:{port}/0"
    finally:
        server.shutdown()


@pytest.fixture
def real_redis(fake_redis_server, monkeypatch):
    """Points the app's live Redis client at the fake server for one test."""
    settings = get_settings()
    monkeypatch.setattr(settings, "redis_url", fake_redis_server)
    redis_client_module.reset_for_tests()
    yield fake_redis_server
    redis_client_module.reset_for_tests()


# ---- Startup requirement (Task 1) -------------------------------------------------------------


def test_staging_refuses_to_start_when_redis_is_unreachable(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", Environment.STAGING)
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")  # nothing listens here
    with pytest.raises(RuntimeError, match="Redis is required"):
        verify_redis_at_startup(settings)


def test_staging_starts_fine_once_redis_is_actually_reachable(client, real_redis, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", Environment.STAGING)
    verify_redis_at_startup(settings)  # must not raise


def test_development_never_requires_redis(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", Environment.DEVELOPMENT)
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")
    verify_redis_at_startup(settings)  # must not raise, Redis stays optional


def test_readiness_endpoint_fails_when_staging_requires_redis_and_it_is_down(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", Environment.STAGING)
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 503
    assert res.json()["redis"] == "unreachable"


def test_readiness_endpoint_passes_when_staging_requires_redis_and_it_is_up(client, real_redis, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", Environment.STAGING)
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 200
    assert res.json()["redis"] == "ok"


# ---- Cross-"worker" sharing (Task 1: "verify ... across multiple workers") --------------------


def test_token_revocation_is_visible_across_independent_connections(client, real_redis):
    """Two separate redis.Redis client connections to the same server --
    standing in for two separate backend worker processes, each of which
    would hold its own cached connection via get_redis(). A revocation
    written through one must be visible through the other immediately."""
    revoke_jti("shared-jti-1", ttl_seconds=60)
    # A second, independent client -- not the cached one get_redis() reused.
    other_worker_client = redis_lib.Redis.from_url(real_redis)
    assert other_worker_client.exists("revoked-jti:shared-jti-1")
    assert is_jti_revoked("shared-jti-1") is True


def test_session_version_bump_is_visible_across_independent_connections(client, real_redis):
    key = "user:shared-subject-1"
    assert get_session_version(key) == 0
    bump_session_version(key)
    other_worker_client = redis_lib.Redis.from_url(real_redis)
    assert int(other_worker_client.get(f"session-ver:{key}")) == 1
    assert get_session_version(key) == 1


# ---- Concurrent refresh-token rotation (Task 1) -----------------------------------------------


def test_concurrent_claim_of_the_same_refresh_jti_only_lets_one_through(client, real_redis):
    """The exact race Phase 10 asks to be verified: many threads racing to
    rotate the SAME refresh token at once. Exactly one must "win" (treated
    as the legitimate rotation); every other concurrent attempt must see
    it as already claimed (the reuse-detection path)."""
    jti = "race-jti-1"
    results: list[bool] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(20)

    def attempt():
        barrier.wait()
        won = claim_jti(jti, ttl_seconds=60)
        with results_lock:
            results.append(won)

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 20
    assert results.count(True) == 1, "exactly one concurrent claim should win"
    assert results.count(False) == 19


# ---- Failure and recovery (Task 1) -------------------------------------------------------------


def test_rate_limiter_fails_open_when_redis_drops_mid_run(client, real_redis, monkeypatch):
    """rate_limit.py's documented choice: a Redis command failure after a
    successful connection falls back to in-process limiting for that call,
    rather than blocking every request."""
    from app.core.rate_limit import limiter

    limiter.check("fail-open-key", limit=100, window=60, message="nope")  # works against the real fake server
    # Simulate the connection dying mid-run by invalidating the cache and
    # pointing at a dead address -- the next call must not raise.
    monkeypatch.setattr(get_settings(), "redis_url", "redis://127.0.0.1:1/0")
    redis_client_module.invalidate()
    limiter.check("fail-open-key", limit=100, window=60, message="nope")  # must not raise
    limiter.hit("fail-open-key")  # must not raise


def test_redis_recovers_after_an_outage_within_the_recheck_window(client, real_redis, monkeypatch):
    """redis_client.py retries a previously-unreachable Redis at most once
    per RECHECK_INTERVAL_SECONDS rather than caching "down" forever (the
    pre-Phase-10 behavior) -- confirmed by forcing a failure, then pointing
    back at the real server and fast-forwarding the recheck clock."""
    settings = get_settings()
    good_url = settings.redis_url
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")
    redis_client_module.reset_for_tests()
    assert redis_client_module.get_redis() is None  # down

    monkeypatch.setattr(settings, "redis_url", good_url)
    # Still within the recheck window -- stays down without a fresh probe.
    assert redis_client_module.get_redis() is None
    # Force the window to have elapsed, then confirm it reconnects.
    redis_client_module._last_probe_failed_at = time.monotonic() - redis_client_module.RECHECK_INTERVAL_SECONDS - 1
    assert redis_client_module.get_redis() is not None
