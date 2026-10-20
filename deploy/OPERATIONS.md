# Running BuildOS AI in production

Everything here uses `deploy/docker-compose.prod.yml`. Commands are run from the repo root.
`$COMPOSE` below means:

```bash
COMPOSE="docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.production"
```

## Still to decide before a real launch

These need choices that haven't been made yet, so they are not set up:

- **Domain and TLS (BUILD-139).** The stack publishes the frontend on port 3000 and the API on 8000 over plain HTTP. Put a TLS-terminating reverse proxy (Caddy, nginx, or a cloud load balancer) in front, and set `FORWARDED_ALLOW_IPS` to its address so login rate limits see real client IPs.
- **Database hosting (BUILD-136).** The stack runs Postgres in a container with a Docker volume. A managed Postgres (RDS, Cloud SQL, etc.) would give you automatic backups and failover. To use one, drop the `db` service and point `DATABASE_URL` at it.
- **S3-compatible object storage (BUILD-138, Task 3).** `STORAGE_BACKEND=local` (the default, and the only backend this project has ever actually run against) keeps using the `uploads` Docker volume. Setting `STORAGE_BACKEND=s3` plus `S3_BUCKET`/`S3_REGION`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` (and `S3_ENDPOINT_URL` for a non-AWS provider) switches to it -- implemented and tested against `moto`'s mocked S3 (`tests/test_storage_s3_http.py`), never against a real bucket. Files already saved to local disk are **not** migrated automatically when switching backends.

## First deploy

1. `cp deploy/.env.production.example deploy/.env.production` and fill it in. The backend **refuses to start** in staging/production with the default JWT secret, the example database password, localhost CORS origins, a missing `TRUSTED_HOSTS`, an unreachable Redis, or `EMAIL_PROVIDER=console` (Phase 9.1/10 safety checks).
2. `$COMPOSE up -d --build`
3. Check: `curl http://localhost:8000/api/v1/health/ready` should return `{"status":"ok","database":"ok","redis":"ok"}`.

The backend runs `alembic upgrade head` every time it starts, so the database schema is created on first start and updated on every deploy.

## Updating

```bash
git pull
$COMPOSE up -d --build
```

Take a backup first (below). Migrations run automatically when the new backend container starts. If one fails, the container exits and the old schema is untouched (Postgres DDL is transactional).

## Health and logs

- `GET /api/v1/health` is liveness: the process is up.
- `GET /api/v1/health/ready` is readiness: it can reach the database, and (Phase 10) it reports real, freshly-probed Redis status too -- `{"status": "ok", "database": "ok", "redis": "ok"}`. In staging/production, an unreachable Redis makes this 503 even though the process keeps serving degraded, single-process-correct responses in the meantime (see "Scaling limits" below) -- that's intentional, so the orchestrator restarts/alerts rather than quietly tolerating it. The backend container's Docker healthcheck uses this endpoint.
- `$COMPOSE logs -f backend` shows one line per request:
  `request_id=... method=GET path=/api/v1/projects status=200 duration_ms=12.3`
  Every response carries the same ID in its `X-Request-ID` header, so a user's error can be matched to its log line. Query strings are never logged. Set `LOG_LEVEL=DEBUG` for more detail.

## Backups

`deploy/backup.sh` writes two files to `./backups` (or `BACKUP_DIR`):

- `buildos-db-<time>.dump`, the database (`pg_dump` custom format)
- `buildos-files-<time>.tar.gz`, uploaded documents and photos (`STORAGE_BACKEND=local` only -- see below for `s3`)

It checks each file is readable before keeping it, and deletes backups older than `KEEP_DAYS` (default 14). Schedule it daily and **copy the backups off the server**. Example cron:

```
0 2 * * * cd /srv/buildos && deploy/backup.sh >> /var/log/buildos-backup.log 2>&1
```

**If `STORAGE_BACKEND=s3`:** the files half of `backup.sh` doesn't apply -- object durability/versioning is the storage provider's job, not this app's. Enable bucket versioning (and cross-region replication if the provider supports it) on the real bucket once one is provisioned; there is nothing for this project's own backup script to do for S3-held files beyond what the provider already offers.

## Restoring

Restore into a running stack (this **replaces** the current data):

```bash
$COMPOSE stop backend frontend
$COMPOSE exec -T db sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/buildos-db-<time>.dump
$COMPOSE run --rm -T --no-deps --entrypoint sh backend -c 'rm -rf /app/storage_data/* && tar -xzf - -C /app/storage_data' < backups/buildos-files-<time>.tar.gz
$COMPOSE start backend frontend
```

**Restore verification, actually executed (Phase 10, Task 5), 2026-10-21:** `pg_dump --format=custom` of the real dev database, restored with `pg_restore --clean --if-exists --no-owner` into a fresh scratch database (`buildos_restore_test`), confirmed identical table count (90) and matching row counts on spot-checked tables, then the scratch database was dropped. This was run directly against this project's dev Postgres with the `pg_dump`/`pg_restore` commands above (not through the Docker Compose stack, since no Docker is available on this development machine) -- it proves the dump/restore mechanism itself is sound, not that the full containerized restore procedure (which also restores the `uploads` volume) has been run end-to-end. Practise the full containerized procedure on a spare machine before relying on it in a real incident.

## Monitoring (Phase 10, Task 6)

No metrics/alerting service (Prometheus, Datadog, Sentry, etc.) is wired into this project -- that's still a genuine, unfilled gap, not newly closed this phase. What exists to monitor against, and what to point an external monitor at once one is chosen:

- **Backend availability**: poll `GET /api/v1/health` (liveness) and `GET /api/v1/health/ready` (readiness, includes real Redis status as of Phase 10).
- **Redis health**: `/health/ready`'s `"redis"` field; in staging/production, unreachable Redis there means the orchestrator should restart/page, not that the app has necessarily gone fully down (it degrades, see "Redis" above).
- **Database health**: `/health/ready`'s `"database"` field, or the `db` service's own `pg_isready` Docker healthcheck.
- **HTTP errors**: `$COMPOSE logs -f backend`'s structured lines (`status=5xx`); every 500 also logs a full traceback via `RequestLogMiddleware`. No log aggregation/alerting is wired up -- this is "grep-able," not "alerts you."
- **Failed email**: query `email_delivery_logs` for `status IN ('failed', 'not_configured')` -- no scheduled job does this automatically today; it's a manual/future-automation query.
- **Background job failures**: this project has no background job runner (no Celery/RQ/etc.) -- nothing to monitor here because nothing exists here. If/when one is added, this section should be revisited.
- **Disk/storage capacity**: the `uploads`/`pgdata`/`redisdata` Docker volumes have no automated capacity check -- host-level disk-space monitoring (standard for any Docker host) is the only thing covering this today.
- **Backup failure**: `deploy/backup.sh` exits non-zero on a failed/corrupt backup (it verifies each file before keeping it) -- wire its cron invocation's exit code into whatever alerting is chosen; it doesn't push an alert itself.

## Scaling limits to know about

- **Rate limiting and session revocation share state across workers/containers** via Redis (`app/core/rate_limit.py`, `app/core/token_store.py`), which is required and startup-checked in staging/production as of Phase 10. In development/test, where Redis stays optional, both fall back to in-process memory -- fine for one worker, wrong for several (each would keep its own counts and its own revoked-token list, so a token revoked on worker A would still work against worker B). Don't run more than one backend worker/container in development without a real reachable Redis.
- **Migrations on start** assume a single backend container. With several, run `alembic upgrade head` as a separate one-off step instead.
- **Single backend worker today** (`Dockerfile.prod`'s `--workers 1`) even though Redis now makes multi-worker rate limiting/revocation correct -- increasing worker count is a reasonable next step once Redis is actually provisioned in a real deployment, not attempted in this phase since "do not purchase infrastructure... without explicit approval."

## Staging deployment (Phase 9.1, hardened Phase 10)

The same `deploy/docker-compose.prod.yml` stack works for a staging environment: set `ENVIRONMENT=staging` instead of `production` in `deploy/.env.production` (a closed, typed set -- see `app/core/config.py`'s `Environment` enum). Staging is held to the **same** safety checks production is (real secret, real DB password, strong bcrypt, no localhost CORS, real `TRUSTED_HOSTS`, reachable `REDIS_URL`, a real `EMAIL_PROVIDER`) -- there is no separate, looser staging profile, so a staging deploy can never accidentally run with production's unsafe defaults.

## Redis (Phase 9.1, required as of Phase 10 Task 1)

**Required** in staging/production -- the backend refuses to start (`app.core.redis_client.verify_redis_at_startup`) if `REDIS_URL` isn't reachable at boot. It backs shared rate limiting and token revocation across workers/containers (`app/core/rate_limit.py`, `app/core/token_store.py`). If Redis drops *after* a successful start: rate limiting fails open (keeps serving, logs a warning, re-probes automatically within 10 seconds of the next request after it comes back); the revocation/session-version checks fail closed (502 `RedisUnavailableError` on the affected request) rather than silently treating a revoked token as valid. `/health/ready` always reports real, current Redis status either way. **No real managed Redis has ever been used by this project** -- this behavior is verified against `fakeredis`'s real Redis-protocol TCP server (`tests/test_redis_integration_http.py`: cross-connection sharing, concurrent refresh-token-rotation races, failure, and automatic recovery), not a production-shaped Redis cluster.

## Email delivery (Phase 9.1, Task 3; required provider as of Phase 10 Task 2)

`EMAIL_PROVIDER` defaults to `console` in development/test (a real sandbox: logs the message and records it as `SIMULATED` in `email_delivery_logs` -- deliberately not the same word a real provider's success uses, so it's never mistaken for one). **Refused outside development/test** -- staging/production must set `EMAIL_PROVIDER=smtp` plus `SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD`; without `SMTP_HOST`, sends are honestly recorded `NOT_CONFIGURED`. A real send that's accepted by the server records `ACCEPTED`; one that fails records `FAILED` with the real error, and `email_service.retry_failed_email()` can retry it in place (same log row, no duplicate) -- there's no background worker in this project to do that automatically, so today it's a function an admin action or a future worker calls. Every send is retry-safe at the send layer too: callers pass a stable `dedup_key`, enforced by a real unique database constraint, so a retried request can never double-email. **No real SMTP credentials have been used in this project** -- the real `smtplib` dial-out code is verified against a real, local SMTP server (`tests/test_email_smtp_http.py`, using `aiosmtpd`), not a live third-party provider or a real inbox.
