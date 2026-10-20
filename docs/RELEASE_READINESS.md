# BuildOS AI — Release Readiness

Written at the end of Phase 9.1 (Production Launch Hardening), 2026-10-21. Supersedes the Phase 9 version of
this file. States the actual, evidence-backed condition of the system — not an aspiration. See
`deploy/OPERATIONS.md` for how to run it; this file does not repeat that, only what's verified versus not.
"Verified working" means covered by an automated test that is currently passing (534 backend tests,
`tsc --noEmit` clean, `next build` clean — 99 routes, 4/4 Playwright e2e tests passing against a real Chrome
browser) or exercised live against the dev Postgres this phase; it does not mean verified in a production
environment, since this system has never been deployed to one.

## 1. Resolved security blockers (this phase)

- **Server-side token revocation, now real.** Every JWT already carried a `jti`; nothing ever checked it. Added
  `app/core/token_store.py`: a per-token denylist (`revoke_jti`/`is_jti_revoked`) and a per-subject session
  version (`get_session_version`/`bump_session_version`), backed by Redis when reachable, falling back to
  in-process memory otherwise. Every token now also carries an `sv` (session version) claim checked on every
  request (`app/api/deps.py`).
- **Logout and logout-all, on all three auth systems.** `POST /auth/logout` (and the `/platform/auth/` and
  `/supplier-portal/auth/` equivalents) revokes the calling access token immediately; `.../logout-all` bumps the
  subject's session version, killing every token for that subject — verified with a test that logs in twice,
  calls logout-all from one session, and confirms both sessions are dead afterward.
- **Refresh-token rotation and reuse detection.** `rotate_refresh_or_reject()` (`app/core/security.py`) revokes
  a refresh token's `jti` the moment it's used; presenting the same refresh token again is treated as a reuse
  attack and poisons the *entire* session (bumps the session version), not just that one token — verified: the
  rotated-away original 401s, and so does the token correctly issued from the rotation afterward. Applied to
  `/auth/refresh`, `/platform/auth/refresh`, and `/supplier-portal/auth/refresh`. Deliberately **not** applied
  to `/supplier-portal/auth/select-supplier`, which is a repeatable scoping step on an already-valid session
  (a multi-supplier user switches which supplier they're acting as), not a single-use refresh.
- **Session invalidation on suspension/deactivation/password change.** Changing a password
  (`user_service.change_password`), deactivating a user (`user_service.update_user`), and suspending a company
  (`platform_company_service.set_company_suspended`, which now sweeps every user in that company) all bump the
  affected session version(s) — verified by reusing an already-issued, still-unexpired token after each change
  and confirming it's dead, not just confirming a *new* login would fail.
- **Rate limiting is now Redis-shared, not just in-process.** `app/core/rate_limit.py`'s `SlidingWindowLimiter`
  uses a Redis sorted set per key when Redis is reachable, falling back to the original in-process behavior
  otherwise — so multiple backend workers/containers finally share one count instead of each enforcing its own.
- **Typed, closed environment detection.** `environment` is now an `Environment` enum (`development` / `test` /
  `staging` / `production`), not a free string — a typo or an unrecognized value is rejected at startup by
  pydantic, instead of silently skipping every safety check the way the old `environment != "production"`
  string comparison did. **Staging is now held to the same checks as production** (secret strength, DB
  password, bcrypt rounds, CORS, and the new `TRUSTED_HOSTS` requirement below) — there is no separate, looser
  staging profile.
- **`TRUSTED_HOSTS` enforcement.** A new required setting outside development/test; `TrustedHostMiddleware` is
  wired into `app/main.py` whenever it's set, rejecting requests with a mismatched `Host` header.
- **Secrets can no longer leak into logs or tracebacks.** `jwt_secret_key`, `llm_api_key`, and `smtp_password`
  are now `pydantic.SecretStr` (every call site uses `.get_secret_value()` explicitly); `Settings.__repr__` is
  overridden to also redact `DATABASE_URL`'s password. Verified directly: `repr(settings)` with a real DB
  password in it prints `***`, not the password.

## 2. Remaining security/infrastructure blockers

- **Redis is optional, not required.** Everything above degrades to the pre-Phase-9.1, single-process-only
  behavior when Redis isn't configured or isn't reachable (true of every environment this project has run in
  so far — there is no running Redis on this machine). That degraded mode is **still correct for a single
  worker**, just not shared across several. Before running more than one backend worker/container, `REDIS_URL`
  must point at a real, reachable Redis.
- **No cross-process distributed lock beyond Redis's own atomicity** — the token-store and rate-limiter
  operations used (`INCR`, `SETEX`, sorted-set `ZADD`/`ZCARD`) are each individually atomic in Redis, but there
  is no multi-step transaction wrapping them; this is the standard, accepted pattern for this kind of counter
  and limiter, not a known gap.
- **No issuer claim / single shared secret** across all three token types (distinguished only by the `type`
  claim, which is sufficient today since this is one deployment, not several federated services). Worth adding
  if BuildOS AI is ever split across separate backend services.
- **Per-product image upload** on the marketplace catalog is still not implemented (flagged in the Phase 7 log;
  unrelated to this phase's security work, restated here only for completeness).

## 3. Required production environment variables

New or changed this phase (see `deploy/.env.production.example`, which has been updated to match):

| Variable | Required in production? | Notes |
|---|---|---|
| `ENVIRONMENT` | Yes | Must be exactly `production` (or `staging`, held to the same checks) — any other value is now rejected at startup, not silently accepted. |
| `TRUSTED_HOSTS` | Yes, outside development/test | Comma-separated or JSON list of the real API host(s). |
| `REDIS_URL` | Recommended once running >1 worker | Falls back to in-process state if unset/unreachable — correct for one worker only. |
| `EMAIL_PROVIDER` | No (defaults to `console`) | Set to `smtp` for real delivery. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS` | Only if `EMAIL_PROVIDER=smtp` | Without `SMTP_HOST`, email is honestly recorded `NOT_CONFIGURED`. |
| `EMAIL_FROM_ADDRESS` | Only if sending real email | |
| `APP_BASE_URL` | Recommended | Used only to build links inside emails (invitation/reset URLs); not security-sensitive. |
| `JWT_SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `BCRYPT_ROUNDS` | Yes (unchanged from Phase 8) | Still validated the same way, now also enforced for `staging`. |

## 4. Infrastructure decisions requiring approval

- **Whether/when to stand up a real Redis instance** for the deployment target, and whether to run more than
  one backend worker (which now depends on that Redis being reachable for rate limiting and session revocation
  to stay correct).
- **Which SMTP/transactional-email provider to use** (SES, SendGrid, Postmark, etc.) and procuring its
  credentials — `EMAIL_PROVIDER=smtp` is implemented and ready, but has never been pointed at a real provider.
- **Object storage (S3-compatible)** — still a local-disk-only implementation (`BUILD-138`, unresolved); needs a
  provider choice and credentials before any real customer file leaves this machine.
- **Domain/TLS/reverse proxy** — still unresolved (`BUILD-139`); the stack serves plain HTTP today.
- **Managed vs. containerized Postgres** — still unresolved (`BUILD-136`).

## 5. Staging deployment guide

Using the existing `deploy/docker-compose.prod.yml` stack (no new compose file needed):

1. `cp deploy/.env.production.example deploy/.env.staging` and fill it in exactly as for production, with
   `ENVIRONMENT=staging` instead of `production` — the same secret/CORS/bcrypt/trusted-host checks apply; there
   is no relaxed staging profile.
2. Point `REDIS_URL` at a real Redis if this staging environment will run more than one backend worker;
   otherwise the single-process fallback is correct but won't scale past one worker.
3. `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.staging up -d --build`.
4. `curl http://<host>:8000/api/v1/health/ready` should return `{"status":"ok","database":"ok"}`.
5. Leave `EMAIL_PROVIDER=console` (the default) unless real SMTP credentials are available for this
   environment — console mode is a real, inspectable sandbox (logs the email, records it `SENT`), safe to use
   in staging without risking a real send to a real inbox.
6. This has not been executed on real staging infrastructure by this agent — no staging host has been
   available in any session of this project. The steps above are the documented procedure, not a confirmed
   live run.

## 6. Backup and restore procedure

Unchanged this phase; documented in full in `deploy/OPERATIONS.md` (`deploy/backup.sh`, `pg_restore`/tar
restore steps). Still not executed end-to-end on this machine (no running production or staging stack to back
up) — restated here because Task 7 asked for it explicitly, not because anything changed.

## 7. Monitoring checklist

Already in place, confirmed still accurate (`deploy/OPERATIONS.md`):
- [x] `/api/v1/health` (liveness) and `/api/v1/health/ready` (readiness, real DB check)
- [x] Structured per-request logs with `X-Request-ID`, no query strings logged
- [x] Secrets never appear in `Settings`' own repr/logs (Phase 9.1, see §1)
- [ ] No metrics/alerting service is wired in (no Prometheus/Datadog/etc. — a genuine gap, not newly introduced)
- [ ] No alert exists today for "Redis unreachable, rate limiting/session revocation silently degraded to
      single-process mode" — this would be a valuable alert to add before relying on Redis in production

## 8. Browser QA results

**Playwright now runs successfully on this machine** (Chrome is installed; it wasn't exercised as a true
end-to-end browser suite in earlier phases' write-ups the same way it was this phase). `frontend/playwright.config.ts`
already existed from an earlier phase; this phase actually ran it:

| Spec | Result |
|---|---|
| `auth.spec.ts`: sign-up creates a company and lands on the dashboard | ✅ pass |
| `auth.spec.ts`: wrong password refused, right one signs in, logout returns to login | ✅ pass |
| `invite.spec.ts`: an admin invites someone, who joins with the given role | ✅ pass |
| `procurement.spec.ts`: RFQ → compare quotes → award → approve PO → pay, overpayment refused | ✅ pass |

4/4 passed, real Chrome, ~6.6 minutes. This covers the company-portal golden path end-to-end in a real browser,
including real page rendering, form submission, and navigation — not just API assertions.

**Not covered by this run** (acceptance-matrix gap, not a false claim): the supplier portal, platform admin,
and public marketing site have no Playwright specs at all — only the three company-portal flows above exist as
browser tests. Mobile-viewport, accessibility, and visual/console-error checks were not part of this run either
(the existing specs don't assert on any of that). No new Playwright specs were written this phase; the existing
3-spec suite was discovered, fixed (see below), and run, not expanded — expanding it to the acceptance-matrix
breadth Task 6 describes (A–F workflows × preconditions/steps/expected/actual/evidence/status) is explicitly
**not done** and would be a meaningfully sized follow-up, not something achievable inside "keep changes small."

One fix was required to make the suite runnable at all: the e2e harness (`backend/scripts/e2e_server.py`) sets
`ENVIRONMENT=test`, which the new closed `Environment` enum (§1) initially rejected — added `test` as a fourth,
explicitly-recognized value (treated identically to `development`: skips the production/staging safety checks).

## 9. Full test results

- **Backend**: `534 passed, 0 failed` (519 at the end of Phase 9 + 15 new/updated this phase: 12 in the new
  `tests/test_auth_hardening_http.py` covering refresh rotation/reuse, logout/logout-all, session invalidation
  on password-change/suspension, and AI quota enforcement+isolation; 2 updated in
  `tests/test_api_authorization_http.py`'s global public-endpoint allow-list for the new
  `/auth/forgot-password`/`/auth/reset-password` routes; 1 updated + 1 added in `tests/test_public_site_http.py`
  for the new email-provider behavior).
- **Frontend**: `tsc --noEmit` clean; `next build` clean, 99 routes (97 at the end of Phase 9 + the new
  `/forgot-password` and `/reset-password` pages).
- **Migration drift check**: clean against the real dev Postgres, using the project's existing
  `compare_metadata`-based check (same one CI runs). Two pre-existing drift entries from Phase 7
  (`ix_supplier_invitations_token_hash`, `ix_supplier_users_email` — a unique index vs. a unique constraint,
  the same harmless representation difference the check already allow-listed for two other columns) were found
  **not actually on the CI allow-list** despite being the same class of difference as what was already there —
  fixed by adding them to `.github/workflows/ci.yml`'s `UNIQUE_AS_CONSTRAINT` set. This was pre-existing drift
  from an earlier phase, not something introduced this phase, but it would have failed CI's drift-check job the
  next time it ran, so it's fixed here rather than left for someone to debug blind.
- **Cross-portal security regression**: `tests/test_security_audit_http.py` (18 tests) and the new
  `tests/test_auth_hardening_http.py` (12 tests) both pass against the current code.
- **Playwright e2e**: see §8 — 4/4 passed.

## 10. Go/no-go recommendation

**No-go for production**, same conclusion as Phase 9, for reasons that are now narrower and more specific:

- **Still blocking**: no real email provider has ever been used (console-sandbox only); no real Redis has ever
  been reachable from this codebase (every "Redis-backed" claim above is "falls back correctly when absent,"
  not "verified under real multi-worker load"); no object storage, domain, or TLS decision has been made; no
  staging or production host has ever actually run this stack.
- **No longer blocking, as of this phase**: the single largest Phase-9-era gap — no server-side token
  revocation at all — is now resolved and tested. Rate limiting is no longer hard-coded to single-process
  behavior (it upgrades automatically once Redis is reachable). The production-environment check can no longer
  be bypassed by a typo or an unrecognized environment name.
- **Recommended next step before any go-live conversation**: stand up one real Redis instance and one real SMTP
  (or equivalent) provider in a staging environment using §5's guide, and re-run the full Playwright suite
  against that staging deployment rather than the dev-SQLite e2e harness — nothing in this phase has been
  verified against infrastructure that doesn't already exist on this single development machine.

## Files changed this phase (Phase 9.1)

New: `backend/app/core/token_store.py`, `backend/app/core/redis_client.py`, `backend/app/models/ai_usage.py`,
`backend/app/services/ai_quota_service.py`, `backend/app/models/password_reset.py`,
`backend/app/services/email_templates.py`, `backend/tests/test_auth_hardening_http.py`,
`backend/alembic/versions/0032_ai_usage_counters.py`, `0033_email_delivery_dedup.py`,
`0034_password_reset_tokens.py`, `frontend/src/app/forgot-password/page.tsx`,
`frontend/src/app/reset-password/page.tsx`.

Modified: `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/core/rate_limit.py`,
`backend/app/api/deps.py`, `backend/app/main.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/platform.py`,
`backend/app/api/v1/supplier_portal.py`, `backend/app/api/v1/platform_ai.py`, `backend/app/api/v1/ai.py`,
`backend/app/api/v1/rfqs.py`, `backend/app/api/v1/marketplace.py`, `backend/app/services/auth_service.py`,
`backend/app/services/platform_auth_service.py`, `backend/app/services/supplier_auth_service.py`,
`backend/app/services/user_service.py`, `backend/app/services/platform_staff_service.py`,
`backend/app/services/supplier_invitation_service.py`, `backend/app/services/notification_service.py`,
`backend/app/services/public_site_service.py`, `backend/app/services/subscription_service.py`,
`backend/app/services/entitlement_service.py`, `backend/app/services/email_service.py`,
`backend/app/models/__init__.py`, `backend/app/models/platform_notification.py`, `backend/app/schemas/billing.py`,
`backend/app/schemas/auth.py`, `backend/app/ai/llm.py`, `backend/tests/test_units.py`,
`backend/tests/test_api_authorization_http.py`, `backend/tests/test_public_site_http.py`,
`frontend/src/lib/billing-types.ts`, `frontend/src/app/billing/page.tsx`, `frontend/src/app/login/page.tsx`,
`.github/workflows/ci.yml`, `deploy/.env.production.example`, `deploy/OPERATIONS.md`, `docs/daily-log.md`,
`docs/tickets.md`, `docs/RELEASE_READINESS.md`.

## Remaining limitations (restated plainly)

No real deployment has ever happened — staging or production. No real email has been sent through a real
provider. No real Redis has ever been reachable from this codebase in any session. No real screenshot or
visual/accessibility browser check has ever been taken (Playwright now runs and passes, but only for 3
company-portal specs with no visual/accessibility assertions — see §8). No load testing has been performed. No
security review beyond this project's own self-audit has occurred. Treat every "verified" claim above as
"verified by this project's own tests and this agent's own live checks on one development machine," not as
independent third-party verification or a confirmed run against real production-shaped infrastructure.
