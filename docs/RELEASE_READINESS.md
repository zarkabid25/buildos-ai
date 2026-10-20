# BuildOS AI — Release Readiness

Written at the end of Phase 9 (PLAT-048..052), 2026-10-20. States the actual, evidence-backed condition of the
system — not an aspiration. See `deploy/OPERATIONS.md` for how to run it; this file does not repeat that, only
what's verified versus not. "Verified working" below means covered by an automated test that is currently
passing (519 backend tests, `tsc --noEmit` clean, `next build` clean) or exercised live against the dev
Postgres this phase; it does not mean verified in a production environment, since this system has never been
deployed to one.

## Verified working

- **Core ERP**: projects, inventory, procurement, finance, workforce, equipment, daily reports, documents,
  BOQ-vs-actual, forecasting, scheduling, search — covered across 20+ test files, tenant isolation asserted
  directly (cross-company 404s, not just hidden UI).
- **Three independent auth systems** (tenant, platform staff, supplier) with distinct token-type claims; cross-
  token rejection verified in `test_security_audit_http.py` for every pairing, including a completely forged
  token against all three.
- **Membership/account status re-checked on every request, not just at login**: a revoked supplier membership,
  a deactivated company user, and a suspended company all lose access immediately through an already-issued,
  unexpired access token (verified directly by reusing the same token after the state change).
- **SaaS billing**: subscriptions, invoices, payment-proof upload/review, entitlements, revenue dashboard
  (earned/invoiced/collected/outstanding kept distinct from MRR, which is computed from ACTIVE subscriptions
  only).
- **Marketplace commissions**: agreements (versioned, rate snapshots preserved on historical entries), append-
  only ledger, commission invoices/payments, disputes/adjustments posted as new reversal entries (originals
  never edited), revenue dashboard that never counts marketplace order value as BuildOS revenue.
- **Supplier self-service portal**: independent auth/memberships, multi-supplier membership with explicit
  active-supplier selection, catalog management, RFQ inbox and quotation submission, order/delivery visibility,
  read-only commission statements — all isolated per supplier (verified: an unrelated supplier gets 404, not a
  filtered view).
- **Public site, onboarding, support**: demo requests and supplier applications create real CRM/application
  records (never auto-verified, never auto-granted marketplace access, confirmed live); one support-ticket
  schema serving company and supplier requesters with internal notes filtered server-side (absent from the
  response, not just hidden in the UI).
- **AI features** (Phase 9, PLAT-048): RFQ summaries and quotation-comparison explanations (company portal),
  RFQ summaries/checklists (supplier portal), CRM lead insights, revenue-trend summaries that keep SaaS and
  commission revenue in clearly separate sections, and supplier-match explanations (platform admin). All
  single-shot, advisory-only, built only from data the caller already fetched through an existing authorized
  service call — the AI can structurally never see or invent data outside that. No AI path creates, awards,
  pays, or adjusts anything; every financial/inventory action still requires a human to act through the
  existing approval flows.
- **Rate limiting gaps found and fixed this phase**: `/auth/refresh`, `/platform/auth/refresh`, and the entire
  supplier-portal auth surface (login, select-supplier, refresh, invitation-info, accept-invite) had no
  throttling at all before this audit; all now limited and covered by tests that drive each one past its limit
  and assert 429.
- **Private file access**: the five file-serving service functions (invoice payment proofs, daily-report
  photos, documents, supplier verification documents, public application documents) all filter by both the
  parent record's id and the file's id — confirmed by direct code read, not inference. Path traversal is
  blocked in `app/core/storage.py`.
- **Production config refuses to start** with a default JWT secret, the example DB password, `bcrypt_rounds`
  below 12, or empty/localhost CORS origins, when `environment == "production"`.
- **Migrations**: clean upgrade/downgrade round-trip on Postgres; the drift check CI runs after every change
  reports no unexpected drift as of this phase (the two flagged unique-constraint/index differences are on
  CI's existing allow-list, not new).

## Tested but not live-verified in production

- Everything above was exercised against pytest fixtures (SQLite + Postgres in CI) and, for several phases,
  against the real dev Postgres on this machine — never against a deployed production stack, since one has
  never been stood up.
- `deploy/docker-compose.prod.yml` / `Dockerfile.prod`: `next build`, migrations, and production config
  validation are all verified; the actual container images have never been built or run, because this machine
  has no Docker available to this session.
- Backup/restore (`deploy/backup.sh`): the script and its documented restore procedure in `deploy/OPERATIONS.md`
  have not been executed end-to-end on this machine (no running production stack to back up).
- UI/design QA (mobile responsiveness, empty/loading states, accessibility, console errors) across the public
  site and all three portals: no browser automation tool has been available in any session of this project.
  Every page renders and builds without TypeScript or build errors, and each has explicit loading/error/empty-
  state branches written in the code (`ErrorState`, `Skeleton`, empty-list copy) — but none of this has been
  visually confirmed in a real browser. This is the same limitation documented on every prior UI-touching day
  in `docs/daily-log.md`.

## Not implemented

- **Server-side token revocation.** A `jti` is minted on every JWT but never stored or checked. There is no
  logout endpoint on any of the three auth systems. A refresh token is never invalidated once issued — it can
  be reused indefinitely until it expires, even after a new one is issued from it. This is the single largest
  security gap found this phase. Fixing it properly needs a revocation store (Redis is already in the stack)
  and is a large enough change that it was not attempted under this phase's "keep changes small" constraint.
- **`ai_monthly_messages` plan limit enforcement.** The field exists on a billing plan and is displayed, but
  nothing currently stops a company from exceeding it on the existing chat copilot (the new Phase 9 narration
  endpoints do have their own, separate per-actor rate limit — that one is enforced).
- **Per-product image upload** on the marketplace catalog (flagged in the Phase 7 log; `MarketplaceProduct` has
  no image field).

## Blocked pending credentials/infrastructure

- **Email delivery.** No SMTP/SES/SendGrid credentials exist in any environment this project has run in.
  `email_service.send_email()` honestly records every attempt as `NOT_CONFIGURED` with a real
  `EmailDeliveryLog` row rather than pretending delivery succeeded — but no email has ever actually been sent.
  Needs a real provider and credentials before go-live if any workflow depends on it reaching an inbox.
- **Object storage (S3-compatible).** Uploads currently go to a local Docker volume (`BUILD-138`, unresolved).
- **Domain/TLS.** No reverse proxy or certificate is configured (`BUILD-139`, unresolved); the stack serves
  plain HTTP.
- **Managed database / multi-worker deployment.** The rate limiter is in-process memory
  (`app/core/rate_limit.py`); it silently stops being an effective limit the moment there's more than one
  backend worker or container, and nothing currently alerts on that. Needs Redis wiring before scaling out.

## Requires manual approval before use

- **Any production deployment or production data change.** Nothing in this project has written to a production
  database or deployed a production container; this phase's "never deploy to production" rule was followed
  throughout.
- **Enabling a differently-named non-"production" environment for real traffic.** The startup safety check in
  `app/core/config.py` only gates on the literal string `environment == "production"` — a staging/UAT
  environment running under any other name would skip the secret/CORS/bcrypt checks entirely. Rename
  discipline or a broader check is a manual decision, not something fixed silently this phase.
- **Setting real commission rates, subscription prices, or supplier verification decisions** — all already
  draft-then-approve or staff-gated by design; this just restates that nothing in this phase changed that.

## Known structural risks, not fixed this phase (flagged, not silently left out)

1. No refresh-token rotation/revocation (see above).
2. In-process rate limiting breaks under multiple workers with no warning (see `deploy/OPERATIONS.md`'s
   existing "Scaling limits" section).
3. Production-environment detection is a literal string match.
4. `ai_monthly_messages` is cosmetic, not enforced, on the pre-existing chat copilot.

## Cross-portal security audit results (PLAT-049)

All of the following were specifically checked this phase (`tests/test_security_audit_http.py`,
`tests/test_rate_limit_http.py`, plus direct code reads where noted): token type/audience validation (pass —
structurally impossible to cross), issuer/signing config (shared secret, no issuer claim currently used —
acceptable for a single-deployment system, worth adding if this is ever split across services), refresh
rotation/revocation (gap, documented above), logout invalidation (gap — no logout endpoint exists at all on any
system), membership/role status on every request (pass, verified live), password reset/invitation security
(pass — invitation lookup returns identical 404 for a real-looking guess as for a nonexistent one, no
information leak), rate limiting (gap found and fixed this phase), safe error responses (pass — no stack
traces or internal detail observed in any tested error path), secure file access (pass, verified by direct code
read), tenant isolation (pass, extensively tested), financial authorization (pass — commission agreement
management and settlement both require OWNER/ADMIN staff, SUPPORT role refused with 403; invoice download and
payment-proof download both require the owning company's own authenticated user), public-endpoint abuse (pass —
demo requests, supplier applications, and all three auth login paths are now rate-limited).

## End-to-end business workflow verification (PLAT-050)

Coverage exists across the full test suite for all six required workflows, though it accumulated phase-by-
phase rather than as one consolidated PLAT-050 pass written from scratch this phase:

- **A. Company onboarding** — `test_public_site_http.py`, `test_auth_http.py`: registration, no auto-
  grandfathering, demo-request lead creation/dedup, duplicate-submission handling.
- **B. Marketplace procurement** — `test_marketplace_integration_http.py`, `test_rfq_http.py`,
  `test_supplier_portal_http.py`: RFQ → invite → quote → award → PO → delivery, cross-tenant isolation at every
  step, an uninvited/declined supplier blocked, a plain non-marketplace PO staying fully invisible to any
  supplier.
- **C. SaaS billing** — `test_billing_http.py`, `test_platform_http.py`: subscribe, invoice, submit payment
  proof, review it, entitlements reflecting plan state, cross-company proof-download isolation.
- **D. Supplier onboarding** — `test_public_site_http.py`, `test_platform_marketplace_http.py`,
  `test_supplier_portal_http.py`: application → staff approval (never auto) → still-pending verification →
  separate verification step → invitation → portal login.
- **E. Support** — `test_public_site_http.py`: ticket creation/reply for both requester types, internal-note
  isolation, cross-tenant/cross-supplier isolation, staff actions audited.
- **F. Financial adjustments** — `test_commissions_http.py`: ledger reversal entries for disputes/adjustments,
  originals never mutated, OWNER/ADMIN-only settlement.

What's explicitly *not* covered as a single scripted "retry/duplicate" and "failure-recovery" pass per
workflow: most workflows have a duplicate/idempotency test (e.g. demo-request dedup, duplicate quotation
revision, repeated review-attempt refusal) but not a uniform matrix of all five failure modes × all six
workflows. Treat this section as "the real gaps are isolated and tested where found," not "every combination
was exhaustively driven."

## Operational reliability (PLAT-051)

Already in place and verified, documented in full in `deploy/OPERATIONS.md` (not repeated here): structured
per-request logging with `X-Request-ID`, `/health` liveness and `/health/ready` readiness (with a real database
connectivity check), documented backup/restore procedure, documented migration-rollback story (transactional
DDL, container exits without touching the old schema on a failed migration). Failed-email visibility is
explicit (`EmailDeliveryLog` with a `NOT_CONFIGURED` status, not a silent pretend-success). Not newly built this
phase; confirmed still accurate.

## Release blockers (in priority order, if this were headed to real users)

1. No refresh-token revocation/logout — a stolen refresh token has no remediation path today.
2. No email provider configured — any workflow that depends on an email actually arriving will not work.
3. No TLS/domain and no object storage decision — required before any public deployment regardless of app-
   level readiness.
4. Rate limiter is single-process-only — must move to Redis before running more than one backend instance.

## Files changed this phase

`backend/app/core/config.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/platform.py`,
`backend/app/api/v1/supplier_portal.py`, `backend/app/api/v1/ai.py`, `backend/app/api/v1/rfqs.py`,
`backend/app/api/v1/marketplace.py`, `backend/app/api/v1/router.py`, `backend/app/ai/llm.py`,
`backend/app/schemas/ai.py`, `backend/app/ai/narrate.py` (new), `backend/app/api/v1/platform_ai.py` (new),
`backend/tests/test_ai_narration_http.py` (new), `backend/tests/test_security_audit_http.py` (new),
`backend/tests/test_commissions_http.py`, `backend/tests/test_supplier_portal_http.py`,
`frontend/src/components/ai-narration-panel.tsx` (new), `frontend/src/app/rfqs/page.tsx`,
`frontend/src/app/marketplace/[id]/page.tsx`, `frontend/src/app/supplier-portal/rfqs/[id]/page.tsx`,
`frontend/src/app/platform-admin/crm/[id]/page.tsx`, `frontend/src/app/platform-admin/commissions/revenue/page.tsx`,
`docs/daily-log.md`, `docs/tickets.md`, `docs/RELEASE_READINESS.md` (new).

No Alembic migration was needed this phase — every change was either additive-free (reusing existing tables/
fields) or purely application-layer (rate limiting, AI endpoints).

## Remaining limitations (restated plainly)

No real deployment has ever happened. No real email has ever been sent. No real screenshot or browser check has
ever been taken, in this phase or any before it. No load testing has been performed. No security review beyond
this project's own self-audit has occurred. Treat every "verified" claim above as "verified by this project's
own tests and by this agent's own live checks," not as independent third-party verification.
