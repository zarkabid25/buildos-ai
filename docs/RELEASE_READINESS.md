# BuildOS AI — Release Readiness

Written at the end of Phase 10 (Infrastructure and Staging Readiness), 2026-10-21. Supersedes the Phase 9.1
version of this file. States the actual, evidence-backed condition of the system — not an aspiration. See
`deploy/OPERATIONS.md` for how to run it; this file does not repeat that, only what's verified versus not.
"Verified working" means covered by an automated test currently passing, or an action actually executed on this
development machine (e.g. a real restore test, below) — never an aspiration or a description of what *should*
work. No staging or production host, no real Redis, no real SMTP provider, and no real S3 bucket have ever
existed for this project; every "backend X is implemented and tested" claim below means tested against a real,
protocol-compatible local test double (fakeredis, aiosmtpd, moto) — never a mock of this project's own code, but
also never the real managed service.

## 1. Infrastructure architecture

```
                 ┌─────────────┐
   HTTPS/TLS  →  │  reverse     │   (not yet chosen/deployed — BUILD-139)
   (not set up)  │  proxy       │
                 └──────┬───────┘
                        │
        ┌───────────────┼────────────────┐
        ▼                                ▼
 ┌─────────────┐                 ┌──────────────┐
 │  frontend    │   REST/JSON    │  backend       │
 │  (Next.js,   │ ─────────────→ │  (FastAPI,     │
 │  1 container)│                │  1 worker)     │
 └─────────────┘                 └──────┬─────────┘
                                         │
                   ┌─────────────────────┼─────────────────────┐
                   ▼                     ▼                      ▼
            ┌─────────────┐      ┌──────────────┐      ┌───────────────┐
            │  Postgres    │      │  Redis        │      │  object        │
            │  (1 container,│     │  REQUIRED in  │      │  storage       │
            │  pgdata vol) │      │  staging/prod │      │  (local disk,  │
            └─────────────┘      │  (Phase 10)   │      │  default; S3-  │
                                  └──────────────┘      │  compatible,   │
                                                         │  optional)     │
                                                         └───────────────┘
                   outbound: SMTP provider (required in staging/prod, Phase 9.1/10)
                   outbound: Anthropic API (optional — AI features)
```

All four application-tier services (`db`, `redis`, `backend`, `frontend`) are defined in
`deploy/docker-compose.prod.yml`, the same file used for both staging and production (see §6). No Kubernetes —
deliberately, per this phase's instruction. No reverse proxy/TLS termination is in the compose file itself; one
must be placed in front of ports 3000/8000 by whoever actually deploys this.

**What's new this phase vs. Phase 9.1:** Redis and a real email provider are now load-bearing, enforced
infrastructure requirements in staging/production (the backend refuses to start without them), not optional
niceties. A second, swappable object-storage backend (S3-compatible) now exists alongside the original
local-disk one. Nothing in the architecture diagram above changes shape — the same four services — but two of
the boxes (Redis, email) move from "nice to have" to "the backend will not start without this."

## 2. Files changed this phase

New: `backend/app/services/ai_quota_service.py` *(Phase 9.1, unchanged)*; this phase's new files:
`backend/tests/test_storage_s3_http.py`, `backend/tests/test_email_smtp_http.py`,
`backend/tests/test_redis_integration_http.py`.

Modified: `backend/app/core/redis_client.py` (fail-fast startup check, always-fresh health probe, automatic
recovery after an outage, thread-safe connect path), `backend/app/core/token_store.py` (atomic `claim_jti` for
race-safe refresh rotation, fail-closed `RedisUnavailableError` on mid-run Redis command failures),
`backend/app/core/rate_limit.py` (fail-open on mid-run Redis command failures), `backend/app/core/security.py`
(uses `claim_jti`), `backend/app/core/config.py` (staging now requires `TRUSTED_HOSTS` and a real
`EMAIL_PROVIDER`, same as production — previously staging skipped both), `backend/app/main.py` (calls
`verify_redis_at_startup`; a `RedisUnavailableError` exception handler → 503), `backend/app/api/v1/health.py`
(reports real Redis status), `backend/app/core/storage.py` (rewritten: `StorageBackend` abstraction,
`LocalStorageBackend`/`S3StorageBackend`, `get_file_response`/`read_bytes` replace the old `resolve_path`),
`backend/app/services/email_service.py` (`SIMULATED`/`ACCEPTED`/`QUEUED`/`RETRYING` statuses,
`retry_failed_email`), `backend/app/models/enums.py` (`EmailDeliveryStatus` expanded — no migration needed, the
column is `VARCHAR`, not a native Postgres enum), `backend/app/services/document_service.py`,
`backend/app/services/daily_report_service.py`, `backend/app/api/v1/documents.py`,
`backend/app/api/v1/daily_reports.py`, `backend/app/api/v1/billing.py`,
`backend/app/api/v1/platform_marketplace.py`, `backend/app/api/v1/platform_support.py` (all five private-file
download endpoints switched from `resolve_path`+`FileResponse` to `get_file_response`, so they work against
either storage backend unchanged), `backend/tests/test_units.py`, `backend/tests/test_public_site_http.py`,
`backend/tests/test_ops_http.py` (updated for the above), `backend/pyproject.toml` (added `boto3`; dev-only
`aiosmtpd`/`moto`/`fakeredis`), `deploy/docker-compose.prod.yml` (Redis healthcheck + `depends_on`, frontend
healthcheck, new env vars), `deploy/.env.production.example`, `deploy/OPERATIONS.md`, `docs/daily-log.md`,
`docs/tickets.md`, `docs/RELEASE_READINESS.md`.

## 3. Code-level blockers resolved

- **Redis silently-forever-down bug, fixed.** Before this phase, `get_redis()` probed Redis exactly once per
  process and cached "unreachable" forever, even if Redis came back up minutes later. Now re-probes at most
  once per 10 seconds while down, so recovery is automatic — verified against `fakeredis`'s real TCP server by
  forcing a failure, pointing back at a working server, and confirming it reconnects once the recheck window
  elapses.
- **Redis required in staging/production, fail-fast at startup.** `verify_redis_at_startup()` raises and
  prevents the process from ever serving traffic if Redis is unreachable in staging/production — a no-op in
  development/test, where it stays optional exactly as before.
- **Mid-run Redis failure now has an explicit, deliberate policy per subsystem** instead of undefined behavior:
  token revocation checks/writes fail *closed* (`RedisUnavailableError` → 503 — a revoked token can never be
  silently treated as valid just because Redis hiccuped); rate limiting fails *open* (logs a warning, falls back
  in-process for that call — losing a few seconds of rate-limit coverage is a smaller cost than blocking every
  login during a blip). Both verified against the real fake-Redis server.
- **A genuine, previously-latent race condition in refresh-token rotation, found and fixed while writing this
  phase's concurrency test.** The old rotation logic was check-then-set ("is this jti revoked?" then "revoke
  it") across two separate Redis round-trips — two concurrent requests presenting the same refresh token could
  both pass the check before either finished the set, each minting a valid new session from what should have
  been a single-use token. Replaced with `claim_jti`'s atomic `SET ... NX`. A 20-thread concurrent-claim test
  against the real fake-Redis server initially reproduced the race (2 "winners" instead of 1) and caught a
  *second*, unrelated bug in the same pass: `get_redis()`'s own first-connection path had no lock, so many
  threads racing to connect for the first time could each independently (and sometimes unsuccessfully, under
  load) attempt a connection — fixed with a connect-path lock. Both fixes are now verified by the same test.
- **`STORAGE_BACKEND=s3` implemented and tested.** `app/core/storage.py` is now a real two-backend adapter
  (local disk, unchanged behavior; S3-compatible, new) rather than a hardcoded-to-local-disk module with an
  aspirational docstring. All five private-file download endpoints now go through one shared
  `get_file_response()` instead of each building its own `FileResponse` from a local path — verified end-to-end
  (a real document upload + download over the real HTTP API) against `moto`'s mocked S3, including confirming
  the response is a signed, expiring redirect, not a bare public URL.
- **Email delivery status vocabulary expanded and renamed for honesty.** The "console" sandbox provider used to
  record its simulated sends as `SENT` — the exact same word a real provider's success would use. Renamed to
  `SIMULATED` so a sandbox delivery can never be mistaken for a real one in a log line, a test assertion, or (in
  the future) an admin screen. Added `ACCEPTED`/`QUEUED`/`RETRYING` to the status vocabulary and a
  `retry_failed_email()` function, verified against a real local SMTP server (not a mock).
- **Staging previously skipped two of production's safety checks** (`TRUSTED_HOSTS`, and there was no
  `EMAIL_PROVIDER` check at all). Both now apply equally to staging — confirmed by a new test that a staging
  config without `TRUSTED_HOSTS` is refused exactly like production would be.

## 4. Infrastructure decisions requiring approval

Unchanged from Phase 9.1 in substance, narrower now that Redis/email are code-complete and only need real
infrastructure behind them:

- **Provisioning a real, reachable Redis instance** for any staging/production deployment — the backend will
  not start without one now. (Development/test remain unaffected and need nothing.)
- **Choosing and provisioning a real SMTP/transactional-email provider** (SES, SendGrid, Postmark, etc.) and its
  credentials — `EMAIL_PROVIDER=smtp` is implemented and integration-tested against a real local SMTP server,
  never against a live third-party provider.
- **Whether to provision S3-compatible object storage at all.** Deliberately left optional, not required, this
  phase — `STORAGE_BACKEND=local` remains a legitimate choice for staging/production (this project has never
  used anything else in practice). If approved: a bucket, region, and access keys for a real AWS account or
  S3-compatible provider (MinIO, Cloudflare R2, etc.).
- **Domain/TLS/reverse proxy** — still entirely unresolved (`BUILD-139`); the stack serves plain HTTP today, and
  nothing in this phase touched that.
- **Managed vs. containerized Postgres** — still unresolved (`BUILD-136`).
- **A metrics/alerting service** (Prometheus, Datadog, Sentry, etc.) — still none chosen; see §6's monitoring
  checklist for what exists to point one at once chosen.

No infrastructure was purchased, provisioned, or credentialed this phase, per this phase's explicit instruction.
Every claim of "implemented and tested" above means tested against a local, protocol-compatible double — never
a live third-party service.

## 5. Test results

- **Backend**: `552 passed, 0 failed` (534 at the end of Phase 9.1 + 18 new this phase: 4 in
  `test_storage_s3_http.py`, 4 in `test_email_smtp_http.py`, 10 in `test_redis_integration_http.py` — plus 3
  pre-existing tests updated for the new readiness-response shape and email-status rename). Full suite rerun
  clean after every fix along the way, not just at the end.
- **Frontend**: `tsc --noEmit` clean (no frontend changes were needed or made this phase — Phase 10 is entirely
  backend/infrastructure).
- **Migration drift check**: clean against the real dev Postgres. **No new migration was needed this phase** —
  every change was either additive-free (the email status enum lives in a `VARCHAR` column, not a native
  Postgres enum, so adding values needs no `ALTER TYPE`) or purely application-layer (Redis/storage/config).
- **Authentication security regression**: `test_security_audit_http.py` (18 tests) and
  `test_auth_hardening_http.py` (12 tests) both still pass unchanged against the refactored `claim_jti`-based
  rotation logic.
- **Financial regression**: full commission/billing/subscription suites (`test_commissions_http.py`,
  `test_billing_http.py`, `test_platform_http.py`, etc.) pass unchanged — nothing in this phase touched
  financial logic, per this phase's explicit restriction.
- **Storage authorization regression**: `test_documents_http.py`, `test_daily_reports_http.py`,
  `test_billing_http.py`, `test_platform_marketplace_http.py`, `test_public_site_http.py` (126 tests spanning
  every migrated download endpoint) all pass unchanged against the new `get_file_response` call sites —
  confirming the storage-backend swap really is transparent to the authorization checks each endpoint does
  before calling it.
- **Email integration**: `test_email_smtp_http.py` — a real send accepted by a real local SMTP server, a
  real connection failure recorded as `FAILED`, and a successful retry of a previously-failed send, all
  against `aiosmtpd`, not a mocked function.
- **Real, executed backup/restore test** (not simulated — see §6): `pg_dump` of the live dev database,
  restored into a fresh scratch database, table count (90) and spot-checked row counts confirmed identical,
  scratch database dropped. Run directly with `pg_dump`/`pg_restore` against this machine's dev Postgres (no
  Docker available here to run the full containerized procedure).

## 6. Staging deployment checklist

Already verified this phase vs. still awaiting provisioning:

**Already verified (code-level, against local test doubles):**
- [x] Backend refuses to start in staging without `TRUSTED_HOSTS`, a strong `JWT_SECRET_KEY`, a non-default DB
      password, `bcrypt_rounds >= 12`, non-localhost CORS, a reachable Redis, and a real `EMAIL_PROVIDER`.
- [x] `docker-compose.prod.yml`: Redis has a healthcheck and the backend's `depends_on` actually waits for it
      (`condition: service_healthy`), not just "container started." Frontend now has a healthcheck too.
- [x] `/health/ready` reports real database AND Redis status, always freshly probed.
- [x] Migrations run automatically on backend container start (`Dockerfile.prod`'s entrypoint) — unchanged,
      confirmed still accurate.
- [x] A real backup → restore → verify cycle has been executed (§5) — against the dump/restore commands
      directly, not the full containerized stack (no Docker on this machine).
- [x] S3-compatible storage backend implemented and tested against a mocked S3, available via
      `STORAGE_BACKEND=s3` without code changes.
- [x] Real SMTP sending implemented and tested against a real local SMTP server.

**Still awaiting provisioning/approval before a real staging host exists:**
- [ ] A real, reachable Redis instance for that environment.
- [ ] A real SMTP (or equivalent) provider and credentials.
- [ ] A domain name, TLS certificate, and reverse proxy in front of ports 3000/8000.
- [ ] A decision on Postgres hosting (containerized vs. managed).
- [ ] A decision on whether to provision S3-compatible storage at all (optional, not required).
- [ ] Running `deploy/docker-compose.prod.yml` for the first time anywhere outside this writer's head — it has
      never been built or started, because no Docker is installed on this development machine.
- [ ] A metrics/alerting service wired up (§ monitoring checklist in `deploy/OPERATIONS.md`).

**Minimum server requirements** (a starting estimate, not load-tested): 2 vCPU / 4 GB RAM is enough to run all
four containers (Postgres, Redis, backend, frontend) comfortably for a small number of concurrent staging
users; this has not been load-tested in any way, so treat it as a starting point to revisit once real usage
exists. **Recurring costs** (compute, managed Postgres if chosen, a Redis instance, an SMTP provider's sending
tier, S3 storage if chosen, a domain) need separate research against whatever hosting provider is actually
chosen — nothing here should be read as a cost estimate.

## 7. Remaining security risks

Carried forward from Phase 9.1, still true, narrower in scope now:

1. **No issuer claim / single shared JWT secret** across all three token types — acceptable for one deployment,
   worth revisiting only if BuildOS AI is ever split across separate backend services.
2. **Redis's optional-in-development fallback is still single-process-only** — by design, and only ever
   reachable in development if someone deliberately runs a local Redis there; staging/production no longer have
   this gap since Redis is now required and startup-checked.
3. **No metrics/alerting service** — a Redis outage, a spike in FAILED emails, or a backup failure all produce
   signals (an unready health check, a log line, a non-zero exit code) but nothing pages anyone automatically
   yet.
4. **The in-memory rate-limiter/token-store fallback inside a single worker is not distributed-lock-safe across
   threads *beyond* the specific fixes made this phase** (the connect-path lock, and `claim_jti`'s atomicity) —
   other less-contended code paths weren't individually audited for the same class of race, since this phase's
   scope was the specific requirements asked for (Redis requirement, concurrent refresh rotation), not a full
   concurrency audit of every function in these two modules.

## 8. Updated RELEASE_READINESS.md

This file — rewritten in place for Phase 10, following the explicit final-report structure requested, replacing
rather than appending to the Phase 9.1 version (which is preserved in git history).

## 9. Go/no-go recommendation

**Still no-go for a real production launch**, narrower reasons than Phase 9.1:

- **Blocking**: no staging or production host has ever existed for this project; no real Redis, SMTP provider,
  domain, or TLS certificate has ever been provisioned; the Docker Compose stack itself has never been built or
  run on any machine (no Docker available here).
- **No longer blocking, as of this phase**: Redis and a real email provider are now hard requirements the
  backend enforces at startup rather than silent gaps; the storage layer is no longer hardcoded to local disk
  only; a real backup/restore cycle has actually been executed and verified (not just documented); a genuine
  concurrency bug in refresh-token rotation (and a related connection-race bug) were found and fixed by writing
  the tests this phase specifically asked for.
- **Recommended next step, unchanged in spirit from Phase 9.1**: provision one real Redis instance, one real
  SMTP provider, and (if a domain/TLS decision has also been made) actually run
  `deploy/docker-compose.prod.yml` for the first time, on a real machine with Docker, as a genuine staging
  deployment — then re-run this project's Playwright suite and the backup/restore cycle against *that*
  deployment specifically. Nothing in this phase changes the fact that this system has never been deployed
  anywhere outside a single developer's laptop.
