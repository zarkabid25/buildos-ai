# BuildOS AI — Daily Progress Log

Format per day: what shipped, tickets closed, what's next. See `docs/tickets.md` for the full backlog.

---

## Day 1 — 2026-09-17 — Foundation

### Done
- **BUILD-001** Initialize monorepo: `backend/` (FastAPI) + `frontend/` (Next.js), `.gitignore`, Docker Compose, README.
- **BUILD-002** Configure PostgreSQL: `docker-compose.yml` db service, SQLAlchemy engine/session (`backend/app/db/session.py`), declarative base with tenant-aware `TenantBase` (`backend/app/db/base_class.py`), Alembic scaffolded (`backend/alembic/`).
- **BUILD-003** Configure FastAPI: app factory (`backend/app/main.py`), settings via pydantic-settings (`backend/app/core/config.py`), CORS, API v1 router, `/api/v1/health` endpoint.
- **BUILD-004** Configure Next.js: App Router, TypeScript strict mode, Tailwind with the BuildOS design system palette (`frontend/tailwind.config.ts`), global layout, first `AppShell` component (dark sidebar + light content area per spec) and a placeholder dashboard page.
- Wrote `CLAUDE.md` with architecture, tenant-isolation and AI-safety rules for all future ticket work.

### Not yet done today
- Authentication, RBAC, company model (BUILD-005, 006, 007) — next up.
- shadcn/ui not yet wired in (using plain Tailwind for now); will add on Day 2 alongside auth forms.

### Next (Day 2 — Auth + Company + Layout)
- BUILD-005 Authentication (register/login/JWT/refresh/password hashing)
- BUILD-006 RBAC (Super Admin, Company Admin, PM, Site Engineer, Storekeeper, Accountant, Viewer)
- BUILD-007 Company management (CRUD, settings, currency, units)
- Wire shadcn/ui, finalize sidebar navigation with routing

---

## Day 2 — 2026-09-18 — Auth, RBAC, Company

### Done
- **BUILD-005** Authentication: `Company`/`User` SQLAlchemy models with a `UserRole` enum (`backend/app/models/`), bcrypt password hashing + JWT access/refresh tokens (`backend/app/core/security.py`), `auth_service` (register/login/refresh), `/api/v1/auth/register|login|refresh|me` endpoints, hand-written Alembic migration `0001_initial` (companies + users tables, since no live Postgres in this dev environment to autogenerate against).
- **BUILD-006** RBAC: 7 roles per spec (Super Admin, Company Admin, PM, Site Engineer, Storekeeper, Accountant, Viewer) on the `User` model; `require_roles()` FastAPI dependency for role-gated endpoints; every `User`/tenant-owned row carries `company_id` (CLAUDE.md rule 9) and `get_current_user` is the single choke point all protected routes go through.
- **BUILD-007** Company management: `GET/PATCH /api/v1/companies/me` (company-scoped, `PATCH` restricted to Company Admin / Super Admin), `company_service`.
- Frontend auth: `/login` and `/register` pages (react-hook-form + zod validation), `AuthProvider` context (token/user persisted to localStorage), typed `api` fetch client, dashboard now redirects unauthenticated users to `/login` and greets the real logged-in user; logout wired into the topbar.
- Minimal shadcn-style primitives added by hand (`Button`, `Input`, `Label`, `Card`) rather than the shadcn CLI, since this environment has no interactive prompt to drive `npx shadcn init` — same visual contract (design tokens, rounded-card, thin borders).

### Verified
- Backend: fresh venv, `pip install -e .`, app imports cleanly, `/api/v1/health` returns 200 via `TestClient`. Not tested against a live Postgres (no `docker`/`psql` available in this environment) — Alembic migration is hand-reviewed and compiles, but run `alembic upgrade head` and smoke-test `/auth/register` once you have Docker running locally.
- Frontend: `npm install`, `tsc --noEmit` clean, `next build` succeeds (all 4 routes prerender/compile: `/`, `/login`, `/register`, `/dashboard`).

### Next (Day 3 — Projects + Dashboard nav)
- BUILD-011 Project CRUD (model, schema, service, API, frontend list/create)
- BUILD-012 Project dashboard (progress/budget/schedule/health placeholders wired to real data)
- BUILD-008/009/010 Executive dashboard cards driven by real project counts instead of hardcoded zeros
- Wire sidebar nav items to actual routes (currently static labels only)

---

## Day 3 — 2026-09-19 — Projects + real dashboard data

### Done
- **BUILD-011** Project CRUD: `Project` model (tenant-scoped via `TenantBase`, `ProjectStatus` enum: planning/active/on_hold/completed/cancelled), `project_service` (list/get/create/update/delete, duplicate-code guard), `/api/v1/projects` REST endpoints with role-gated writes (PM/Company Admin/Super Admin can write, delete restricted to admins), Alembic migration `0002_projects`.
- **BUILD-012 / BUILD-008** Project dashboard + executive dashboard: `/projects` list + create form (react-hook-form + zod), `/projects/[id]` detail page with stat cards and a tab strip (Overview live, other tabs stubbed for upcoming epics), dashboard stat cards and AI-summary blurb now driven by a real `GET /projects/summary` endpoint instead of hardcoded zeros.
- **Risk heuristic (early BUILD-089 groundwork):** `project_service._is_at_risk()` flags an active project as at-risk when elapsed schedule time outpaces reported progress by >15 points — a placeholder ahead of the full risk engine in Epic 17, documented in code as such.
- Sidebar nav now uses real `next/link` routes with active-state highlighting; unbuilt modules (BOQ, Inventory, etc.) render as disabled labels instead of dead links, so the full IA stays visible without lying about what's clickable.

### Bug found and fixed during verification
- `passlib[bcrypt]` (added Day 2) is incompatible with modern `bcrypt` releases — passlib probes a `bcrypt.__about__` attribute removed in bcrypt 4.1+, causing every `hash_password`/`verify_password` call to crash at runtime. Confirmed by actually installing the pinned deps in a clean venv and running the app (not just reading the code). Replaced passlib with a direct, small `bcrypt.hashpw`/`checkpw` wrapper in `app/core/security.py`; dropped the `passlib` dependency.

### Verified (this time end-to-end, not just import-checked)
- Backend: fresh venv install, then a real in-process test against an in-memory SQLite DB exercising the full flow — register → login (correct password accepts, wrong password correctly rejected with 401) → create project → update progress → summary aggregation (total/budget/avg progress/at-risk count all correct).
- `/api/v1/openapi.json` confirms all routes registered with correct path ordering (`/projects/summary` before `/projects/{project_id}`, otherwise FastAPI would treat "summary" as a project id).
- Frontend: `tsc --noEmit` clean, `next build` succeeds for all 7 routes including the new `/projects` and dynamic `/projects/[id]`.
- Still not tested against live Postgres/Docker (unavailable in this dev environment) — run `docker compose up --build` and `alembic upgrade head` to confirm on real infra.

### Next (Day 4 — Tasks, milestones, project members)
- BUILD-013 Project members (assign users to projects with roles/permissions)
- BUILD-014 Project milestones
- BUILD-015 Project tasks (CRUD, assignment, priority, status, due date)
- BUILD-009 Project health widget (turn the at-risk heuristic into a visible score)

---

## Day 4 — 2026-09-20 — Tasks, milestones, members, health score

### Done
- **BUILD-013** Project members: `ProjectMember` model (unique per project+user), tenant-checked add/remove/list via `project_member_service`, nested `/api/v1/projects/{project_id}/members` endpoints. Members panel on the project detail page.
- **BUILD-014** Project milestones: `Milestone` model, CRUD-lite service (create/list/update — checking a milestone complete auto-stamps `completed_date` if not supplied), nested `/milestones` endpoints, inline add + checkbox-toggle UI.
- **BUILD-015** Project tasks: `Task` model (title/description/assignee/priority/status/due date, `TaskStatus`/`TaskPriority` enums), nested `/tasks` endpoints (any project member can move status; create/delete restricted to PM+), inline add + status-dropdown UI.
- **BUILD-009** Project health widget: `GET /projects/{id}/health` returns per-dimension scores (schedule, cost, inventory, quality, safety, labor, procurement) matching the 7-bar health widget in the product spec. Only `schedule_score` is populated for now — it's derived from the same elapsed-time-vs-progress variance as the Day 3 at-risk heuristic. The other six stay `null` ("no data") rather than showing fabricated numbers, because their source modules (expenses, inventory, daily reports, attendance...) don't exist yet. Frontend renders all 7 as bars, with null ones visibly empty and labeled "no data" instead of silently faked.
- Alembic migration `0003_project_members_milestones_tasks`.

### Why null instead of a fake number
CLAUDE.md's rule against inventing data applies to more than AI output — a hardcoded "72%" cost-health bar with no expense data behind it would be just as misleading as an AI hallucination. Kept the honesty even though a full 7-bar chart looks more finished with all bars filled.

### Verified end-to-end
- Backend: fresh venv install, then a real run against in-memory SQLite covering: create an active project with a 100-day schedule at day 50 / 20% progress → health score correctly shows `schedule_score=40, is_at_risk=True`; task create + status update; milestone create + complete (auto-stamps today's date); project member add; **and two tenant-isolation checks** — adding a user from a different company as a project member is correctly rejected (404), and fetching another company's project by ID is correctly rejected (404).
- `/openapi.json` confirms all 16 routes register with the expected nested paths.
- Frontend: `tsc --noEmit` clean, `next build` succeeds for all routes.
- Still not run against live Postgres/Docker in this environment — run `docker compose up --build` yourself to confirm on real infra.

### Next (Day 5 — BOQ)
- BUILD-016 BOQ management (create BOQ, add/edit/delete items, CSV import)
- BUILD-017 BOQ calculations (quantity × rate = amount, category totals)
- BUILD-018 BOQ vs Actual (estimated/committed/consumed/remaining/variance — mostly stubbed until procurement/inventory exist)
- BUILD-019 AI BOQ assistant (flagged as an estimate requiring professional review, per CLAUDE.md rule 13)

---

## Day 5 — 2026-09-21 — BOQ management + AI BOQ assistant

### Done
- **BUILD-016** BOQ management: `BoqItem` model (item code, description, category, unit, quantity, rate), `boq_service` (list/create/bulk-create/update/delete, all tenant + project scoped), nested `/api/v1/projects/{id}/boq` endpoints, Alembic migration `0004`. CSV import from the spec is deferred — noted as a gap below rather than silently dropped.
- **BUILD-017** BOQ calculations: `amount` is a computed property (`quantity × rate`) on the model rather than a stored column, so it can never drift out of sync; `GET /boq/summary` returns total amount plus per-category subtotals.
- **BUILD-019** AI BOQ assistant: `POST /boq/ai-generate` returns a **draft only** (nothing written to the DB) built from a small rule-of-thumb starter template (cement/steel/sand/bricks/labor/excavation quantities for a generic residential build); `POST /boq/ai-accept` is the separate, explicit call that actually creates the items, following CLAUDE.md's "AI never writes directly" rule. The response always carries a disclaimer that the numbers are estimates needing professional review (rule 13). Frontend shows the draft in a distinct highlighted card with "Add all N items" / "Discard" before anything touches the real BOQ table.

### Important honesty note on BUILD-019
This is **not** a live LLM call. The real AI infrastructure (LLM service, prompt management, structured outputs) is Epic-11-in-the-original-plan work that hasn't been built yet — this environment also has no verified network path to an LLM API to test against. `generate_starter_boq()` is a small deterministic Python template, clearly commented as a placeholder in `boq_service.py`. It satisfies the ticket's UI/workflow contract (draft → review → accept) honestly, but the actual "intelligence" is still ahead of us. Flagging this explicitly so it doesn't get mistaken for working AI later.

### Deferred from BUILD-016
CSV import for BOQ items wasn't built today — cut to keep the day scoped, tracked as a gap rather than silently skipped. Can be added later as a thin endpoint that parses CSV into the existing `bulk_create_items` service function.

### Verified end-to-end
- Backend: fresh venv install, then a real run against in-memory SQLite: created two BOQ items, confirmed `amount` math (1,200 bags × 1,400 = 1,680,000), confirmed category subtotal (1,680,000 + 12,600,000 = 14,280,000 for "Materials"), generated the 8-item AI draft, accepted it and confirmed all 8 came back flagged `is_ai_generated=True`, deleted an item and confirmed the count dropped correctly, and confirmed cross-tenant BOQ access is rejected (404).
- `/openapi.json` confirms all 5 BOQ routes register correctly, including the `/summary` vs `/{item_id}` and `/ai-generate`/`/ai-accept` vs `/{item_id}` ordering (no literal-vs-variable path collisions).
- Frontend: `tsc --noEmit` clean, `next build` succeeds for all routes; new BOQ tab on the project detail page (add-item form, item table with amounts, AI-generate button with a review-before-accept draft card).
- Still not run against live Postgres/Docker in this environment.

### Next (Day 6 — Inventory foundation)
- BUILD-020 Material categories
- BUILD-021 Material CRUD
- BUILD-022 Warehouse CRUD
- BUILD-023 Inventory stock (start of the Project → BOQ → Procurement → Inventory workflow the spec calls the "killer workflow")

---

## Day 6 — 2026-09-22 — Inventory foundation (BUILD-020 through 030)

### Done
- **BUILD-020/021** Material categories + materials: `MaterialCategory`, `Material` models (SKU unique per company, reorder point), CRUD service + `/api/v1/material-categories` and `/api/v1/materials` endpoints.
- **BUILD-022** Warehouse CRUD: `Warehouse` model, service, `/api/v1/warehouses` endpoints.
- **BUILD-023/024/025/026/027/028** Inventory stock, in/out, transfer, allocation, transaction history — all built on one design decision: `InventoryTransaction` is an **append-only ledger**, not a mutable stock-balance table. Current stock on hand is always *derived* by summing signed transaction quantities (`stock_in`/`transfer_in` add, `stock_out`/`transfer_out`/`allocation` subtract) rather than stored and incrementally updated, so a balance can never drift out of sync with its own history — the same reasoning as the BOQ `amount` computed property from Day 5. `stock_out` validates against on-hand quantity and rejects over-withdrawal (400, not a silent negative balance). `transfer` is two linked transactions (`TRANSFER_OUT` + `TRANSFER_IN`) sharing a `transfer_group_id`, validated against the source warehouse's balance. Passing a `project_id` to stock-out records it as `ALLOCATION` instead of a plain `STOCK_OUT`, which is BUILD-027 (project material consumption) — same endpoint, no separate code path needed.
- **BUILD-029/030** Low-stock alerts + inventory dashboard: `GET /inventory/dashboard` returns total materials, low-stock count, out-of-stock count, warehouse count, matching the spec's dashboard numbers. Reorder point is set per-material (company-wide), and low/out-of-stock is evaluated against the material's *total* on-hand quantity across all warehouses combined, not per-warehouse — a deliberate simplification, noted here in case it surprises anyone reading the code later. What's built is the dashboard indicator, not a push/email notification system (that's Epic 19, not started).
- Alembic migration `0005_inventory`.
- Frontend: `/inventory` page — dashboard stat cards, add-material and add-warehouse forms, a stock in/out panel, and a stock-levels table. Sidebar "Inventory" and "Warehouses" links now both route here (single page covers both for the MVP).

### Verified end-to-end
- Backend: fresh venv install, then a real run against in-memory SQLite: stock in 500 → stock out 120 → confirmed balance 380; attempted to withdraw 99,999 → correctly rejected (400, insufficient stock); transferred 80 units between two warehouses → confirmed both sides balanced correctly (300 / 80); dashboard correctly triggered `low_stock_count=1` for a material at 90/100 reorder point and `out_of_stock_count=1` for a material never stocked, in a dedicated test built specifically to catch a wrong threshold check.
- One thing I got wrong on the first pass and caught myself: I initially expected the dashboard to report a specific number based on one warehouse's balance, but the code (correctly, by design) aggregates across all warehouses per material. Re-checked the math and confirmed the code was right, not the test expectation — worth recording since it's exactly the kind of assumption mismatch that's easy to ship silently.
- `/openapi.json` confirms all 11 new routes register correctly.
- Frontend: `tsc --noEmit` clean, `next build` succeeds for all 8 routes.
- Still not run against live Postgres/Docker in this environment.

---

## Fix — 2026-09-18 — Critical auth bug: every authenticated request was broken on SQLite

### What happened
While setting up a local test run for the user (SQLite dev DB, since no Docker/Postgres password was available in that environment), every single authenticated endpoint returned 500. `GET /materials`, `/warehouses`, `/projects/summary`, even `/auth/me` — anything gated by `get_current_user`.

### Root cause
`app/api/deps.py` (`get_current_user`) and `app/services/auth_service.py` (`refresh`) both did:
```python
db.query(User).filter(User.id == payload["sub"]).first()
```
`payload["sub"]` is the JWT subject claim — always a plain **string**. `User.id` is a `postgresql.UUID(as_uuid=True)` column. Against real Postgres, psycopg2 silently coerces a string into the native UUID type, so this works. Against SQLite (no native UUID type), SQLAlchemy's UUID bind processor requires an actual `uuid.UUID` Python object and crashes calling `.hex` on a plain string.

This is exactly the same class of bug as the enum-values fix from earlier today: correct-looking code that only breaks against a specific database backend, invisible to tests that don't exercise the real HTTP+JWT path. My own verification up to this point only ever called service functions directly with real `uuid.UUID` objects (e.g. `owner.company_id`) — I never once drove a request through `get_current_user` itself in an automated test. That's a real gap in the test coverage, not just bad luck.

### Fix
Both call sites now parse `payload["sub"]` into a real `uuid.UUID` before querying, with a clean 401 (not a 500) if the token's subject is malformed:
```python
try:
    user_id = uuid.UUID(payload["sub"])
except (KeyError, ValueError, TypeError):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
user = db.query(User).filter(User.id == user_id).first()
```
This is strictly more correct on Postgres too (explicit conversion instead of relying on driver-level implicit coercion), so it's not a SQLite-only patch.

### Verified
Restarted the local backend, then drove the exact flow the browser was using: register → `GET /materials` (200), `GET /warehouses` (200), `POST /materials` (201, real row created), `POST /warehouses` (201), login → `GET /projects/summary` (200), `GET /auth/me` (200). Every previously-broken authenticated route now works.

### Lesson for future test coverage
Need at least one automated test that goes through the full HTTP stack (TestClient + real JWT in the Authorization header), not just direct service-layer calls — added to the Day 7+ backlog as a standing gap, since BUILD-129 (authentication tests) hasn't been done yet.

---

## Fix — 2026-09-18 — Frontend never refreshed expired access tokens

### What happened
Right after the auth bug above was fixed, the user hit a fresh 401 on every request in the browser. This one wasn't a bug in the backend — it was a missing feature in the frontend. Access tokens expire after 60 minutes; the backend has a working `POST /auth/refresh` endpoint (built Day 2), but the frontend fetch client never called it. Once a token expired mid-session, every subsequent request just failed with 401 until the user manually logged out and back in.

### Fix
- **`frontend/src/lib/auth-store.ts`** (new): a plain module (not a React hook) holding the current access/refresh tokens, so the non-React `api.ts` fetch layer can read the latest refresh token and write a refreshed one back, without threading tokens through every single hook call.
- **`frontend/src/lib/api.ts`**: on a 401 (and only if the request actually carried a token, and it isn't already a retry, and it isn't the refresh call itself), calls `POST /auth/refresh`, updates the store, and retries the original request once with the new access token. Concurrent 401s (several TanStack Query hooks firing at once, exactly what caused the flood of 401s in the logs) are coalesced into a single in-flight refresh request instead of racing multiple refreshes.
- **`frontend/src/lib/auth-context.tsx`**: `AuthProvider` registers two callbacks with the store — `onRefreshed` updates React state + localStorage with the new tokens, `onRefreshFailed` (refresh token also expired/invalid) clears the session, which the existing route guards already handle by redirecting to `/login`.

### Verified
Confirmed the backend's `/auth/refresh` response shape (`access_token`/`refresh_token`/`token_type`) matches exactly what the new frontend code expects, via a direct curl call using a real refresh token. `tsc --noEmit` clean. Did **not** run a separate `next build` against the same `.next` folder the user's live dev server was using this time — learned that lesson from the cache-corruption incident earlier in the day — instead confirmed via the running dev server's own log that Next.js Fast Refresh recompiled all three changed files with zero errors.

---

### Next (Day 7 — AI inventory intelligence, then Procurement)
- BUILD-031 Material consumption analytics (daily/weekly/monthly usage rate from the transaction ledger — real math, no AI needed)
- BUILD-032 Stockout prediction (current stock ÷ consumption rate)
- BUILD-033 AI reorder recommendation (same honesty rule as the BOQ assistant — deterministic math dressed as a recommendation, not a real LLM call, until AI infra exists)
- Start of Epic 8 Procurement (material requests) once inventory intelligence is in place

---

## Day 7 — 2026-09-21 — AI inventory intelligence (BUILD-031..034)

### Done
- **BUILD-031** Material consumption analytics: `forecast_service.get_consumption_rate()` sums `STOCK_OUT` + `ALLOCATION` transactions over a trailing 30-day window (transfers are deliberately excluded — moving stock between warehouses isn't consumption, it nets to zero company-wide) and derives daily/weekly/monthly averages. `GET /inventory/materials/{id}/consumption`.
- **BUILD-032** Stockout prediction: `days_remaining = current_stock / daily_avg_usage`, `estimated_stockout_date = today + days_remaining`. `GET /inventory/materials/{id}/forecast` and `GET /inventory/forecast` (all materials).
- **BUILD-033** Reorder recommendation: when `days_remaining` is at or below a 7-day lead-time buffer, recommends ordering enough to cover 30 days at the current rate (`ceil(daily_avg × 30 − current_stock)`). Unlike the Day 5 BOQ generator, this one is **genuinely computed**, not a placeholder template — it's the same kind of deterministic arithmetic as the project health score, not an LLM call, and doesn't need to be one to be a legitimate recommendation (matches the product spec's own "Order 5,000 bags" example, which is arithmetic, not generative).
- **BUILD-034** Material anomaly detection: flags a material when the last 7 days' daily average consumption is ≥1.5× the prior 23-day baseline. `GET /inventory/anomalies`.
- Frontend: `/inventory` page gains an "AI Inventory Forecast" table (stock, daily usage, days-to-stockout highlighted red under 7 days, recommendation text) and a highlighted "Consumption Anomalies" card when any are detected.

### A real gap I found and fixed during testing, not just after
Built a proper test scenario with backdated transactions (a material with steady ~10/day consumption for 3 weeks, then a spike to 40/day in the most recent week) specifically to exercise the anomaly detector against the forecast together — and it exposed a real problem: the anomaly detector correctly flagged the spike, but the stockout forecast, using a flat 30-day trailing average, was still reporting a comfortable 29-day runway because the older, calmer weeks diluted the average. For a feature whose entire point is catching risk early, silently under-reacting to a spike it had *just* detected itself would have been a real defect, not a nitpick. Fixed by having the forecast use the more conservative (higher) of the 30-day rate and the most recent 7-day rate — re-ran the same scenario and confirmed it now reports 12 days remaining (matching the real recent rate), while a separate steady-state material's forecast was unaffected by the change, and a third scenario confirmed the reorder recommendation itself triggers correctly (3 days remaining → recommends ordering 80 bags to cover 30 days).

### Verified end-to-end
- Fresh venv install, then a test with realistic backdated `InventoryTransaction` rows (not just today's data) covering: consumption rate math (500 total / 30 days = 16.67/day), the spike-detection fix (12 vs. the wrong 29 days), a steady-state material unaffected by the fix, and an explicit reorder-trigger scenario (3 days remaining → 80-bag recommendation, math double-checked).
- `/openapi.json` confirms all 4 new routes register correctly.
- Frontend: `tsc --noEmit` clean (skipped a separate `next build` this time since the live dev server was running — checked Fast Refresh compiled without errors instead, per the lesson from the earlier cache-corruption incident).
- Restarted the live local backend the user has been testing against, confirmed exactly one process listening on port 8000 (no repeat of the earlier duplicate-process problem), health check passes.

### Next (Day 8 — Suppliers)
- BUILD-035 Supplier CRUD
- BUILD-036 Supplier contacts
- BUILD-037 Supplier transaction history
- BUILD-038 Supplier performance (price/quality/delivery/reliability scoring)
- BUILD-039 AI supplier insights (same honesty standard — real math from PO/delivery history, not a fake LLM call)

---

## Day 8 — 2026-09-22 — Suppliers (BUILD-035, 036)

### Done
- **BUILD-035** Supplier CRUD: `Supplier` model, service, `/api/v1/suppliers` endpoints.
- **BUILD-036** Supplier contacts: `SupplierContact` model (nested under a supplier), service, `/api/v1/suppliers/{id}/contacts` endpoints.
- Alembic migration `0006_suppliers`.
- Frontend: `/suppliers` page with a list + add-supplier form. Sidebar link wired up.

### Deliberately not built today: BUILD-037/038/039
Transaction history, performance scoring (price/quality/delivery/reliability), and AI supplier insights all need real Purchase Order and delivery data to mean anything — the spec's own example ("Delivery performance decreased 13%...") is a computed statement about actual order history. Building these now would mean either fabricating plausible-looking numbers or shipping permanently-empty endpoints until Procurement exists, and both break the no-invented-data rule this project has held to since Day 3 (the project health score) and Day 7 (the inventory forecast). Marked as blocked in `docs/tickets.md` rather than checked off, and the `/suppliers` page says so directly instead of pretending the feature is coming from nowhere. Procurement (Epic 8: material requests → purchase orders → goods receipts) is next, which unblocks all three with real data.

### Verified end-to-end
- Fresh venv install, then a real run against in-memory SQLite: created a supplier, added a contact, confirmed contact count, confirmed cross-tenant supplier access is rejected (404), deleted the supplier and confirmed the list is empty afterward.
- `/openapi.json` confirms all 6 supplier routes register correctly.
- Frontend: `tsc --noEmit` clean.
- Restarted the live local backend the user is testing against, confirmed a single clean process on port 8000, health check passes.

### Next (Day 9 — Procurement: material requests → purchase orders → goods receipt)
- BUILD-040 Material request
- BUILD-044 Purchase order (+ BUILD-045 approval workflow, per CLAUDE.md rule 14)
- BUILD-046 Goods receipt
- BUILD-047 Automatic inventory update (goods receipt approval creates real `STOCK_IN` transactions — the payoff of the append-only ledger design from Day 6)
- RFQ/quotation comparison (BUILD-041..043) deferred behind the core PO flow — noted as a scope cut, not silently dropped
- Once real POs exist, circle back and actually build BUILD-037/038/039 with real data

---

## Day 9 — 2026-09-23 — Procurement: the killer workflow closes the loop (BUILD-040, 044..047)

### Done
This is the day the spec's "killer workflow" (Project → BOQ → Material Requirement → Procurement → PO → Goods Receipt → Inventory → Consumption) becomes a real, working, tested path through the system rather than separate unconnected modules.

- **BUILD-040** Material request: `MaterialRequest` + `MaterialRequestItem` models (project-scoped, multi-line), `pending → approved/rejected/converted` status, `/api/v1/material-requests` endpoints.
- **BUILD-044** Purchase order: `PurchaseOrder` + `PurchaseOrderItem` models, auto-generated sequential PO numbers (`PO-1001`, ...), optional link back to the material request that spawned it (auto-marks that request `converted`), `total_amount` computed from line items (same computed-property pattern as BOQ `amount` and inventory stock — never a stored, driftable total). `/api/v1/purchase-orders`.
- **BUILD-045** PO approval: POs are created in `pending_approval` (not `draft` — no RFQ/quotation step exists yet to justify a separate draft stage, see the cut below), and can only move to `approved` via a dedicated `POST /purchase-orders/{id}/approve` endpoint restricted to Company Admin/Super Admin/PM — matches CLAUDE.md rule 14 (approval workflows for important actions). A PO that isn't `pending_approval` can't be re-approved.
- **BUILD-046** Goods receipt: `GoodsReceipt` + `GoodsReceiptItem` models. Receiving is only allowed against an `approved` or `partially_received` PO, and each line is validated against the *remaining* quantity on that PO item (`quantity - quantity_received`), not the original order quantity — so partial receipts across multiple deliveries can't be over-received in total. PO status auto-transitions to `partially_received` or `received` depending on whether every line is fully received.
- **BUILD-047** Automatic inventory update: this is the payoff of the Day 6 append-only ledger design. Every goods-receipt line posts a real `STOCK_IN` `InventoryTransaction` (referenced by PO number) in the same transaction as the receipt itself — inventory reflects reality the moment goods are actually received, no separate manual "stock in" step for anything that came through procurement.
- Frontend: `/procurement` page — material request form, PO creation form, a PO table with status badges and inline Approve / Receive actions (warehouse + quantity inputs appear once a PO is approved). Sidebar "Material Requests" and "Purchase Orders" both route here.

### Scope cut, stated plainly
BUILD-041/042/043 (RFQ, supplier quotations, quotation comparison) are not built. Doing them properly means a real multi-supplier bidding workflow, which is a substantial feature on its own and would have meant either rushing it today or skipping verification depth on the PO/goods-receipt/inventory chain — the actually load-bearing part of the "killer workflow" the whole product spec is built around. Chose depth on the core chain over breadth across every ticket. Marked as deferred, not done, in the tracker.

### Verified end-to-end — the full chain, not just each piece in isolation
Ran one continuous scenario against in-memory SQLite: material request created (pending) → purchase order created referencing it (material request auto-converts, PO total = 500 × 1,400 = 700,000, confirmed) → **goods receipt correctly rejected before approval** → PO approved (approver recorded) → partial receipt of 300/500 → **inventory stock automatically shows 300** (no manual stock-in call) → PO status correctly `partially_received` → **over-receiving the remaining 200 as 9999 correctly rejected** → remaining 200 received → PO status correctly `received` → **final inventory stock = 500**, matching the full PO quantity exactly. Also confirmed cross-tenant access is rejected for both fetching and approving a PO (404). `/openapi.json` confirms all 7 new routes register correctly. Frontend `tsc --noEmit` clean. Restarted the live local backend, confirmed a single clean process on port 8000.

### Next (Day 10 — Finance foundation)
- BUILD-048 Project budget
- BUILD-049 Expense management
- BUILD-051 Project cost calculation (committed = open PO value, actual = received/expensed value — now possible with real PO data)
- BUILD-052 Budget vs actual
- Once expense/cost data exists, this also finally unblocks BUILD-037/038 (supplier transaction history + performance) from Day 8

---

## Day 10 — 2026-09-24 — Finance: budget, expenses, cost forecast (BUILD-048..053, 055..057)

### Done
- **BUILD-048/049/050** Project budget, expense management, expense categories: `ExpenseCategory`, `Expense` models (project-scoped, dated, categorized), `/api/v1/expenses` and `/api/v1/expense-categories`. Project budget itself reuses the `Project.budget` field that's existed since Day 3 — no new model needed there.
- **BUILD-051/052** Project cost calculation + budget vs actual: `GET /projects/{id}/cost-summary` returns original budget, **committed** (sum of every non-cancelled PO's `total_amount` for the project — money earmarked at approval, not just at spend), **actual** (sum of recorded expenses), and **remaining** (`budget − committed − actual`).
- **BUILD-053 / 055 / 056 / 057** Forecast cost, cost variance detection, budget overrun prediction: all the same computation, exposed through one field each. `forecast` is a simple earned-value-style projection — if the project has recorded progress, `forecast = actual ÷ progress% × 100` (the same "spend rate so far, extrapolated to 100% complete" idea real cost control uses); with no progress recorded yet, it honestly falls back to `committed + actual` rather than pretending to project something it can't, and says so in a `forecast_basis` string the UI displays directly. `expected_variance = forecast − budget` *is* both the variance detection and the overrun prediction — a positive number is an overrun, and the frontend color-codes it red/green accordingly. All genuinely computed, no LLM involved (same honesty stance as Day 7's inventory forecast).
- Frontend: new "Costs" tab on the project detail page — a 6-figure budget summary (Original / Committed / Actual / Remaining / Forecast / Expected Variance) matching the spec's Finance Screen layout, plus an expense list + add form.

### Deliberate simplification, stated in the code
"Actual" spend is defined strictly as recorded `Expense` rows — goods receipts do **not** auto-create an expense. Doing so would double-count the same money as both "committed" (via the PO) and "actual" (via an auto-generated expense) unless a receipt also reduced the committed figure accordingly, which adds real complexity for a distinction (accrual timing) that doesn't change the MVP's usefulness. Documented directly in `finance_service.py` rather than silently chosen.

### Deferred: BUILD-054 (cash/payment tracking)
Not built today. The spec explicitly says to keep this lightweight, and expenses already cover "money spent on the project" for cost-control purposes; payment tracking (which invoices are paid vs outstanding) is a distinct concern from project cost visibility and didn't fit today's scope without shortchanging verification on the forecast math. Tracked as a gap, not silently dropped.

### Verified end-to-end
- Fresh venv install, then a real run against in-memory SQLite: created a project with a 1,000,000 budget, a 200,000 PO, and 150,000 in expenses. Checked the cost summary twice — once with no progress recorded (forecast correctly falls back to committed + actual = 350,000) and once after setting progress to 25% (forecast correctly recalculates to 150,000 ÷ 25% = 600,000, variance correctly = 600,000 − 1,000,000 = −400,000). Both hand-worked and asserted in code, not eyeballed.
- Confirmed cross-tenant access to a cost summary is rejected (404).
- `/openapi.json` confirms all 3 new routes register correctly.
- Frontend: `tsc --noEmit` clean.
- Restarted the live local backend, confirmed a single clean process on port 8000, health check passes.

### Next (Day 11 — Workforce + Equipment, then Daily Reports)
- BUILD-063 Employee CRUD, BUILD-064 project assignment, BUILD-065 attendance, BUILD-066 labor cost
- BUILD-068 Equipment CRUD, BUILD-069 project assignment, BUILD-070 maintenance records
- Circle back to BUILD-037/038 (supplier performance) now that real PO/expense data exists to compute it from honestly

---

## Day 11 — 2026-09-25 — Workforce + Equipment (BUILD-063..071)

### Done
- **BUILD-063/064** Employee CRUD + project assignment: `Employee` model (designation, daily wage, hire date), `EmployeeProjectAssignment` join table (unique per employee+project, same pattern as `ProjectMember` from Day 4), `/api/v1/employees` endpoints.
- **BUILD-065** Attendance: `Attendance` model, one record per employee per day (unique constraint — recording twice for the same day is rejected, not silently overwritten), status enum (present/absent/half_day/leave), `/api/v1/attendance`.
- **BUILD-066** Labor cost: `GET /projects/{id}/labor-cost` sums `daily_wage` for every `present` day and half of it for every `half_day`, per project — genuinely computed from the attendance ledger, not estimated.
- **BUILD-067** Basic productivity analytics: `GET /employees/{id}/productivity` returns an attendance rate (`present ÷ total_recorded × 100`) — the "basic" in the ticket name is deliberate; true output-based productivity would need task/unit-completed data this MVP doesn't track yet, so attendance rate is the honest floor for what "productivity" can mean right now.
- **BUILD-068/069/070/071** Equipment CRUD + assignment + maintenance + reminders: `Equipment` model with a `current_project_id` field (assignment is just setting this via `PATCH`, no separate assignment table needed since equipment can only be in one place at a time, unlike employees who can be assigned to multiple projects over time), `EquipmentMaintenance` records, and `GET /equipment/reminders` — flags equipment whose most recent maintenance record's `next_due_date` is overdue or within 14 days. Equipment with **no** maintenance history is correctly excluded from reminders rather than flagged as a false "overdue," which was worth a dedicated test case (see below).
- Frontend: new `/workforce` page (employee list, add-employee form, record-attendance form) and `/equipment` page (equipment list with inline status dropdown, add-equipment form, a highlighted maintenance-reminders card). Sidebar wired up for both.

### Verified end-to-end
- Fresh venv install, then a real run against in-memory SQLite covering the full scenario: two employees, one assigned to a project (duplicate assignment correctly rejected), five attendance records across both (duplicate same-day attendance correctly rejected) — hand-worked expected labor cost (2 present days + 1 half day for a 1,800/day mason = 4,500, plus 1 present day for a 1,200/day laborer = 1,200, total **5,700**) matched exactly; productivity for the laborer (1 present of 2 recorded) matched the expected 50%.
- Equipment reminders: four pieces of equipment — one due in 5 days, one overdue by 3 days, one due in 60 days, and one with **no maintenance history at all**. Confirmed only the two within the 14-day window appear, confirmed the far-future and no-history equipment are correctly excluded (not flagged), and confirmed the overdue one sorts first.
- `/openapi.json` confirms all 10 new routes register correctly.
- Frontend: `tsc --noEmit` clean.
- Restarted the live local backend, confirmed a single clean process on port 8000, health check passes.

### Next (Day 12 — Daily Reports, then Documents)
- BUILD-059 Daily report (weather, workers, work completed, materials consumed, problems, notes)
- BUILD-060 Daily report list
- BUILD-061 Photo uploads (needs object storage — check what's actually available in this environment before committing to a real S3-compatible backend vs. a documented local-disk stand-in)
- BUILD-062 AI daily report generation deferred until real AI infra exists (same honesty rule as BOQ/reorder assistants)
- Then Epic 14 Documents (upload, categories, metadata)

---

## Day 12 — 2026-09-26 — Daily reports, photo uploads, and the first real test suite (BUILD-059..061)

### Done
- **BUILD-059/060** Daily reports: `DailyReport` model (date, weather, workers on site, work completed, materials consumed, equipment, problems, notes), **one report per project per day** enforced by a unique constraint (a second one is a 409, not a silent duplicate), nested under `/api/v1/projects/{id}/daily-reports`. Alembic migration `0010`.
- **BUILD-061** Photo uploads: `DailyReportPhoto` + `POST /daily-reports/{id}/photos` (multipart) and an authenticated download endpoint.
- Frontend: a new **Reports** tab on the project page (`components/daily-reports-panel.tsx`) with a report form, report cards, and per-report photo upload. Photos are fetched as blobs with the auth header because an `<img src>` can't send one.

### Storage: what's real and what isn't
The spec calls for S3-compatible storage. There's no Docker and no object store in this environment, so `app/core/storage.py` is a **local-disk backend behind a small interface** (`save_upload`, `resolve_path`), and callers only ever handle opaque storage keys. Moving to S3/MinIO means replacing those two functions. It is not S3 today, and BUILD-138 (storage configuration) stays open. `storage_data/` is gitignored.

### Upload safety, and its limits
Implemented: content-type allow-list (images only for photos), size cap (`MAX_UPLOAD_BYTES`, default 10 MB), empty files rejected, and the stored filename is a fresh UUID so a hostile client filename (`../../etc/passwd.png`) can never reach the filesystem path; `resolve_path` also refuses keys that escape the storage root. **Not** implemented: content sniffing. The content type is whatever the client declares, so a non-image labelled `image/png` would be accepted (it's served back as a blob to an `<img>`, so the practical risk is low, but it isn't real validation). BUILD-124 is therefore marked partial, not done.

### The first real test suite (closing a gap I'd flagged)
On Day 6 I found that none of my "verified end-to-end" runs had ever gone through real HTTP + JWT, which is how the UUID auth bug shipped. This is the first day that's fixed: `backend/tests/` is a proper pytest suite (temp SQLite DB + temp storage dir per run, tables recreated per test) that registers real users through the API and calls endpoints with a real `Authorization` header.
- `test_auth_http.py` (7): protected routes 401 without a token; `/auth/me` works; a garbage token is a 401, not a 500; a refresh token can't be used as an access token; the refresh endpoint issues working tokens; wrong password is rejected; **cross-tenant project access is a 404**.
- `test_daily_reports_http.py` (9): create/list, one-per-day 409, upload→download byte-for-byte roundtrip, disallowed type 415, oversize 413, empty 400, hostile filename, and another company can neither see the report, download its photo, nor upload to it.
- Result: **16 passed**. The first run had 2 failures, which turned out to be my own test data (a company name too short for the schema) — I confirmed that from the 422 before changing anything, rather than assuming.
- Only auth, tenant isolation on projects, and daily reports are covered. Inventory, procurement, finance etc. are still verified only by the earlier ad-hoc scripts; BUILD-127..134 are not done.

### Not built
BUILD-062 (AI daily-report generation from free text) needs a real LLM integration, which doesn't exist yet.

### Verified
`pytest`: 16 passed. Frontend `tsc --noEmit`: clean. Not yet checked in a browser this session, and still not run against live Postgres.

### Correction to earlier days' "verified" claims
The local SQLite dev database (`backend/buildos_dev.db`) was created once and never refreshed as models were added, so from Day 8 on it lacked the tables for suppliers, procurement, finance, workforce, equipment and (now) daily reports. On Days 8–11 I told the user those pages "should work now" — against their running instance they would have failed with "no such table". My checks all used fresh in-memory databases and never touched the live one. Found on Day 12 by listing the tables (11 of 28 present), fixed by re-running `scripts/init_sqlite_dev_db.py` (`create_all` only adds missing tables, so existing data was preserved), and then verified against the **live** server: all 15 module list endpoints return 200 with a real login, and a project → daily report → photo upload → download → bad-type-rejected (415) round trip works. Lesson: after adding models, re-run the init script before claiming the running app works, and smoke-test the live server, not just a scratch database.

### Next (Day 13 — Documents)
- BUILD-072..075 document upload, categories, download, metadata (reuses the storage layer above)
- Then decide how to handle the AI epics honestly: they need a real LLM key and network access, which I haven't confirmed exist here

---

## Day 13 — 2026-09-27 — Documents (BUILD-072..075)

### Done
- **BUILD-072/073/075** Upload, categories, metadata: `Document` model (title, category — contract/drawing/boq/invoice/report/quotation/other, description, original filename, content type, size, optional `project_id`), multipart `POST /api/v1/documents`, list with `project_id` and `category` filters, `PATCH` for metadata (title/category/description — never touches the stored file), `DELETE` that removes the DB row **and** the file. Migration `0011`.
- **BUILD-074** Preview/download: `GET /documents/{id}/download`, with `?inline=true` for a browser preview. Inline is honoured only for PDF, plain text, CSV and images; anything else (Word/Excel) always downloads as an attachment. Every response carries `X-Content-Type-Options: nosniff`. `text/html` is not in the upload allow-list at all, so an uploaded file can't be served back as a page.
- Frontend: `/documents` page (upload form with category and optional project, category filter, table with Preview / Download / Delete). Files are fetched as blobs with the auth header, since a plain link can't send it. Delete asks for confirmation.
- Permissions: uploading and editing are limited to roles that handle project paperwork (admins, PM, site engineer, storekeeper, accountant); **viewers can read and download but not upload, edit or delete**; delete is admin/PM only.

### Tests (26 total, all passing)
`tests/test_documents_http.py` adds 10 tests through real HTTP + JWT: byte-for-byte upload/download roundtrip (and that the internal `storage_key` never appears in an API response), inline preview allowed for PDF but forced to attachment for `.docx`, `text/html` and `.exe` rejected with nothing written to disk, oversize/empty/missing-title, list filters, metadata edit leaves the file intact, attaching to **another company's project** is a 404 with nothing stored, another company can't read/download/edit/delete (all 404), **a viewer created in the same company is 403 on write actions but can read**, and delete removes the file from storage.
- To test roles at all I added a `make_user_in_company` helper (there's no invite flow, so it inserts the user directly and then logs in through the real API).
- Caught a test-isolation bug of my own before it bit: uploaded files persisted between tests while the DB reset, which would have made "nothing was stored" assertions order-dependent. The autouse fixture now clears storage per test.
- Because everything passed on the first run, I checked the tests can fail: temporarily removing the tenant filter from `get_document` made the cross-company test fail (`200 == 404`, i.e. a real leak), then I restored the file. That's a one-off manual check, not an automated mutation-testing setup.

### Verified live
Before restarting the running backend I added the `documents` table to the dev database (the Day 12 lesson). Against the live server with a real login: upload → 201; list filtered by `category=contract` returns it and `category=drawing` returns nothing; inline download returns `200`, `content-disposition: inline`, `nosniff`, and the file is byte-identical to what was uploaded; an HTML upload gets `415`; delete returns `204` and a follow-up GET is `404`. The frontend page compiles and serves `200`. Frontend `tsc --noEmit` clean.

### Known limits
- Same as Day 12: local-disk storage stand-in (not S3) and no content sniffing, so BUILD-124/138 stay open.
- No virus scanning, no versioning, and deleting a project does not yet clean up its documents.
- Documents can't yet be edited (title/category) from the UI — the API supports it, the page only uploads/filters/previews/downloads/deletes.

### Next
The remaining big block is the AI layer (Epics 15–16: document Q&A, copilot, natural-language analytics) plus scheduling, notifications, search, reports, settings, UX polish, security hardening and deployment. Before starting the AI epics I need to confirm whether an LLM API key and outbound network access actually exist in this environment; if not, I'll say so and build what can be done honestly (e.g. the tool layer and structured-output plumbing) rather than fake model output.

---

## Day 14 — 2026-09-28 — The AI layer, built honestly without an API key (BUILD-083, 085, 090 done; 010, 082, 084, 086–088, 133 partial)

### First, what this environment actually has
Checked before writing anything: **no API key exists** (not in the environment, `LLM_API_KEY` in `backend/.env` is empty) but the network path to `api.anthropic.com` works (HTTP 401 = "auth required"). So a real model call is impossible from here. I did not fake one. This day builds everything *around* the model, so the assistant switches on the moment a key is supplied, and separates clearly what was verified from what wasn't.

### Built
- **Rules-based insights engine** (`app/ai/insights.py`, `GET /ai/insights`): schedule risk, cost-overrun forecast, overdue tasks and milestones, stockout risk, low/out-of-stock, unusual consumption, overdue/upcoming equipment maintenance, POs awaiting approval, material requests not actioned. Every insight has a severity, a plain-English detail, and the supporting numbers. **No language model is involved**; the response carries `generated_by: "rules"` and the UI says so. It only claims a cost overrun once progress has been recorded (with 0% progress the "forecast" is just spend-so-far, not a projection). This powers the dashboard's Executive Summary card (replacing the hardcoded blurb) and a new `/ai-insights` page (BUILD-090).
- **Read-only tool layer** (`app/ai/tools.py`, 12 tools): projects, project overview (health/cost/labor), materials, inventory status + forecasts, stock levels, consumption anomalies, purchase orders, material requests, daily reports, document metadata, company insights, and `propose_material_request`. **`company_id` is never in any tool's input schema**; it always comes from the signed-in user, so the model cannot ask for another company's data. Tool failures come back as error results the model can read, never exceptions. Lists are capped at 25 with a `truncated` flag.
- **Draft-and-approve** (CLAUDE.md rule 12): `propose_material_request` stores an `AiProposal` (a draft) and nothing else — the real `material_requests` table is untouched. A person approves it via `POST /ai/proposals/{id}/approve`, which runs the *existing* `create_material_request` service (same validation as a hand-made request) with the **approver** as the requester. Approving twice is a 409; viewers can see proposals but not decide them.
- **Real Anthropic client** (`app/ai/llm.py`) on the official `anthropic` SDK (added as a dependency — it's the official client), model `claude-opus-5` from `LLM_MODEL` (my earlier `claude-sonnet-5` default was my own guess, not a choice you made; changed, and your local `.env` too). Per the API reference: no `temperature`/`top_p`/`top_k` (Opus 5 rejects them), thinking left at its adaptive default, `stop_reason` checked before reading content (`refusal` handled), and server-side refusal `fallbacks: "default"` **enabled by default** (`LLM_USE_FALLBACKS=false` turns it off).
- **Copilot loop** (`app/ai/copilot.py`): manual tool loop, capped at `LLM_MAX_TOOL_ITERATIONS` (8), all results for one turn returned in a single message. Conversations and messages are persisted (`ai_conversations`, `ai_messages`) and are **private to the user who started them**, not just their company. Migration `0012`.
- API: `GET /ai/status` (never returns the key), `POST /ai/chat` (503 with a clear "set LLM_API_KEY" message when unconfigured; provider errors map to 429/502/503 with generic text and leave no empty conversation behind), conversations, proposals.
- Frontend: **AI Command Center** at `/ai` (honest "isn't switched on yet" banner, insights, the approval queue, chat with suggested questions — disabled until a key exists), `/ai-insights`, and the dashboard card.

### Tests: 58 passing (32 new)
- Insights over real HTTP: empty company, a project that's behind and over budget, low stock, pending POs/requests, no false overrun at 0% progress, a healthy project produces nothing, other companies see none of it.
- Copilot with a **scripted fake model** (this tests *our* loop, not Claude): tool results reach the model; history is saved and replayed; unknown tools and a runaway loop are contained; refusals handled; **cross-company access through tools returns errors and never leaks** (including a smuggled `company_id`); conversation privacy; proposals create nothing until approved; approval gives the person ownership; no double decisions; viewer/other-company blocked; bad proposals (foreign material, zero quantity, no items, malformed id) rejected with no draft; provider failures mapped safely.
- The **exact request the real client sends** is captured through the SDK with a mock transport (model, beta header, `fallbacks: "default"`, tools, no sampling params). This proves the SDK serialises what I intend; it does **not** prove the live API accepts it.
- Checked the safety tests can fail: broke tenant scoping in `list_projects`, allowed viewers to approve, and removed the "still pending" check — each broke exactly the matching test; restored afterwards. A manual check, not an automated mutation suite.
- The suite pins `LLM_API_KEY=""` so it can never call the real API even if a key is later added to `.env`.

### NOT verified, and why it matters
Nothing has run against the real Claude API. Unknown until a key is added: whether the request is accepted (incl. the `fallbacks` beta), how well the model uses these tools, whether answers are good, latency and cost. So BUILD-082/086/087 are marked **partial**, not done. The first real-key session should be: set `LLM_API_KEY`, ask the five suggested questions, and read the answers against the data.

### Deliberately not built
- **Document Q&A / RAG (BUILD-076–081):** needs text extraction, chunking and an embeddings provider. Anthropic offers no embeddings endpoint, so this needs a separate provider decision (or lexical search) — not something to guess at.
- BOQ/daily-report/procurement AI generation, semantic search, AI cost/risk explanation text, settings UI for the model.
- Streaming responses, and prompt caching (fine to add once real usage shows it matters).
- `propose_material_request` is the only proposal type; no PO drafts yet.

### Next
Set an API key and verify against the real model (highest value), then the non-AI gaps: scheduling/Gantt, notifications, search, settings, reports, UX polish, security hardening, deployment.

---

## Day 15 — 2026-09-29 — Scheduling: dependencies, variance, a basic Gantt (BUILD-092..097)

### Done
- **BUILD-093** Tasks with dependencies: `TaskDependency` join table (`task_id` cannot start until `depends_on_task_id` is done). Cycle detection is a real graph check, not just "not itself": adding `A -> B` is rejected if `B` already (directly or transitively) depends on `A`, walked via `_depends_transitively()`. Same-project and same-company checks reuse `get_task`, so a dependency can't reach into another project or company.
- **BUILD-092/096** Project schedule + basic Gantt: `Task` gets a `start_date` column (it only had `due_date` before). `GET /projects/{id}/schedule` returns tasks, milestones, and the variance below in one call. Frontend: a new **Schedule** tab renders task bars and milestone diamonds positioned by date with plain CSS (no charting library) — colored by task status, a dependency add/remove UI underneath. No drag-to-reschedule or zoom; it's a read view plus a simple form, which is what "basic" means here.
- **BUILD-097** Schedule variance: reused the elapsed-vs-progress math from the Day 3 at-risk heuristic and the Day 9 project health score (same formula, no new logic invented), but made it public (`project_service.get_schedule_variance_percent`, previously a private helper only `_is_at_risk`/`get_health` could see) and added a days version (`get_schedule_variance_days`) so the UI can say "40 days behind" instead of a bare percentage.
- **BUILD-094/095** Milestones and progress tracking were already built (Day 4, Day 3) — marked done in the tracker rather than left unchecked now that the schedule view actually surfaces them together.
- Not built: **BUILD-098 AI delay analysis** needs the real LLM connection from Day 14, which is still unverified against the live API.

### Verified end-to-end
- Fresh venv install, full suite: **70 passed** (12 new: start/due dates round-trip, add/remove a dependency, self-dependency rejected, duplicate dependency rejected (409), a direct 2-node cycle rejected, an indirect 3-node cycle rejected, cross-project and cross-company dependency targets rejected (404), schedule with no dates has no variance, schedule variance hand-checked against a concrete scenario (100-day project, day 50, 20% progress → 30 points / 30 days behind), milestones appear on the schedule, tenant isolation on the schedule endpoint).
- **Mutation check on the part most likely to be subtly wrong** (cycle detection, not the simpler CRUD): removed the `_depends_transitively` guard, confirmed both cycle tests failed (`201` instead of `400`) rather than passing vacuously, restored the code, confirmed both pass again.
- Live server: same lesson as Day 12/14 applied again — `create_all` only adds missing *tables*, not columns to a table that already existed (`tasks` predates today), so I had to `ALTER TABLE tasks ADD COLUMN start_date` by hand on the dev DB before restarting, or every task create would have 500'd on the live server despite all tests passing. Caught this before it became a repeat of the Day 12 mistake, not after. Then: created a project with real dates, added a dependency, confirmed the cycle-closing attempt is rejected with the exact error message, and hand-verified the schedule math against the running server (58/90 days elapsed → 64%, minus 20% progress = 44% / 40 days behind — matches by hand). Frontend `/projects` compiles and serves 200 with the new Schedule tab; no errors in the dev server log.

### Next
Notifications, search, settings, reports, UX polish, security hardening, deployment — or verifying the AI layer against a real API key if one becomes available.

---

## Day 16 — 2026-09-30 — Notifications: 4 real triggers, not a static bell (BUILD-099, 100)

### Done
- **BUILD-099** Notification system: `Notification` model (recipient, type, title, body, an in-app link, read state). `notify_users_with_roles()` fans out one row per matching active user in the company, excluding whoever triggered the event — nobody gets told about their own action. Wired into four real events, each mirroring the exact role set the corresponding API endpoint already restricts writes to (so "who gets notified" always matches "who's actually allowed to act"):
  - **Task assigned** — `task_service.create_task`/`update_task` now take the acting user's id, and only fire when the assignee changes *and* isn't the actor. Reassigning doesn't double-notify the old assignee.
  - **Material request submitted** — notifies the same roles that can approve one (`procurement.py`'s `CAN_APPROVE`, mirrored as `APPROVER_ROLES` in the service since API-layer role tuples shouldn't be imported into the service layer).
  - **Purchase order created** — same approver set, title includes the PO number.
  - **AI proposal drafted** — notifies the same roles that can approve/reject a proposal (`ai.py`'s `CAN_DECIDE`), so the Day 14 draft-and-approve loop now actually tells someone there's something to review instead of relying on them checking `/ai` unprompted.
- **BUILD-100** Notification center: a bell in the topbar (`components/notification-bell.tsx`) — unread badge (polls every 30s), dropdown list, click-to-navigate-and-mark-read, mark-all-read. Unread rows are visibly highlighted.

### A real bug I found in my own test, and fixed the test instead of hiding it
My first mutation check targeted the wrong thing: I removed the self-notify guard from `update_task` and both "self-notify" tests still passed — because neither one actually exercised self-assignment *via* `PATCH` (one used `create_task`, the other reassigned to a *different* person). The mutation passed vacuously; it proved nothing. Added `test_self_assigning_via_update_does_not_self_notify`, reran the same mutation, and this time it correctly failed (`assert [...] == []` with a leaked notification) before I restored the guard. Recording this because "the mutation check passed" is only meaningful if you first confirm the test you're relying on can actually fail — I didn't check that the first time, and it would have shipped a false sense of coverage.

### A flake, reported honestly rather than either ignored or oversold
The full 82-test suite failed once, on the very first complete run today, with `AttributeError: 'float' object has no attribute 'replace'` inside `uuid.UUID()`, in `test_ai_copilot_http.py::test_bad_proposals...[bad_id]` — a test file I didn't touch today. It did not reproduce: not in isolation, not re-running that whole file (25/25), not in a 3-file subset with today's new tests, and not on a full clean rerun (82/82). I looked for an unstr'd `uuid.UUID()` call that could explain a stray float and didn't find one that fits the failing test's code path. I'm not claiming to have fixed this — I don't have a diagnosis, only a single non-reproducing occurrence. Flagging it here instead of either quietly rerunning until green (which is how flaky-but-real bugs get shipped) or claiming a fix I can't justify.

### Verified live, and found a self-inflicted bug in my own verification method along the way
To test a second-user scenario against the running server, there's no "invite a teammate" endpoint yet, so I inserted a second user directly into the dev SQLite database. My first attempt used raw `sqlite3` with a manually formatted UUID string, and login worked but `/auth/me` then failed with "Invalid or expired token" — a real bug, but in my test setup, not the product: SQLAlchemy's UUID type on SQLite serializes differently (no dashes) than a hand-written UUID string (with dashes), so a row written by raw SQL doesn't match what a subsequent ORM query for that same id looks for — the exact same category of type-coercion mismatch as the Day 6 enum bug, just self-inflicted this time via my own shortcut rather than shipped code. Fixed by inserting through the ORM (`SessionLocal` + `User(...)`) instead, which is also what the test suite's `make_user_in_company` helper already does correctly. Once fixed: task assignment, material request, and PO notifications all confirmed correct against the live server (right recipient, right exclusion, right title/link), plus mark-all-read.

### Not built
No "invite a colleague" flow exists yet (Epic 12 doesn't have one either) — the only way a second real user joins a company today is a developer/admin action, not a self-serve UI flow. Real-time push (websocket/SSE) isn't built; the bell polls every 30 seconds instead.

### Next
Search, settings, reports, UX polish, security hardening, deployment remain. Or verify the AI layer against a real API key if one becomes available.

---

## Day 17 — 2026-10-01 — Global search (BUILD-101)

### Done
- **BUILD-101** Global search: `GET /search?q=` does case-insensitive substring matching across projects (name/code/client), tasks (title), materials (name/sku), suppliers (name), purchase orders (number), documents (title/filename), and employees (name/designation) — 7 entity types in one call, each result carrying a link to where it actually lives in the app. Uses `.ilike()`, which SQLAlchemy compiles to a `LOWER()`-based comparison on backends without native `ILIKE` (SQLite), so it behaves the same on SQLite here and Postgres in production. No new table, no migration — it's a pure read over existing data.
- Below a 2-character query, or no query at all, it returns an empty result rather than doing a full-table scan.
- Frontend: the topbar's static "Search..." placeholder (there since Day 1) is now a real debounced (250ms) search box with a grouped dropdown, replacing the last piece of the shell that was still decorative rather than functional.
- **BUILD-102** (AI semantic search) not built — same reason as everything else AI: needs an embeddings provider decision that hasn't been made (Day 14).

### Verified end-to-end
- Fresh venv, full suite: **95 passed** (13 new — one per entity type, case-insensitivity, cross-type results in one query summing correctly in `total`, the below-minimum-length guard, a clean empty result with no error, and tenant isolation).
- **Mutation check on the highest-stakes property in a feature that spans 7 tables**: removed the `company_id` filter from the project search branch. The isolation test caught it immediately and concretely — `assert 'Company A Secret Tower' not in [...]` failed because it *was* in Company B's results. Restored, confirmed the full file (13/13) and the isolation test individually both pass again.
- Live: searched the real dev database for "cement" and got exactly the three real Cement-named materials that exist there (from this week's testing) with correct subtitles: no fabricated or stale results. Confirmed the 1-character and empty-query guards both correctly return zero results without erroring. Frontend `tsc --noEmit` clean; `/dashboard` and `/projects` both serve 200 with no errors in the dev server log.
- Note: the previous session ended mid-turn (background dev servers were killed when it did); this session started by confirming nothing was still listening on 8000/3000, then started both fresh rather than assuming stale state was still good.

### Next
Settings, reports, UX polish, security hardening, deployment remain. Or verify the AI layer against a real API key if one becomes available.

---

## Day 18 — 2026-10-02 — BOQ vs Actual (BUILD-018)

### Done
- **BUILD-018** BOQ vs Actual. A BOQ line can now be linked to an inventory material (`boq_items.material_id`, nullable, migration `0015`). `GET /projects/{id}/boq/vs-actual` compares each linked line's planned quantity with the stock **allocated to that project** (the `ALLOCATION` rows in the inventory ledger), giving actual quantity, quantity variance, variance %, and a status (`not_tracked`, `not_started`, `within_plan`, `over_plan`). Materials used on the project that no BOQ line covers are listed separately as unplanned consumption.
- Actual amount is actual quantity × **BOQ rate**, so the variance is a quantity variance, not a price variance; the response says so in `valuation_note`. Pure arithmetic over the ledger, no estimates (CLAUDE.md rule 11).
- Linking rules: the material must belong to the same company (404 otherwise), its unit must match the BOQ line's unit (case- and whitespace-insensitive; 400 otherwise, since cement in bags can't be compared with cement in kg), and a material can back only one line per project (409), or its usage would be counted twice. Checked on create, update (including changing the unit of a linked line), and bulk AI-accept.
- **Tenant fix found along the way:** `POST /inventory/stock-out` accepted a `project_id` without checking the project belonged to the caller's company. Allocations now drive per-project reporting, so it now 404s on a foreign project.
- Frontend: the BOQ form has an "Inventory material" picker (fills in the unit), server errors are shown under the form, and a **BOQ vs actual** card sits under the BOQ table.

### Tests: 107 passing (12 new, `tests/test_boq_vs_actual_http.py`)
Hand-checked scenario (100 bags planned, 120 allocated in two stock-outs → +20 / +20.0% / over plan; 40 m3 planned, 30 used → −10 / −25.0% / within plan; totals 2000 planned vs 1950 used at BOQ rate), unlinked and not-started lines, zero planned quantity (no %), unplanned consumption, other projects' allocations and plain stock-outs don't count, unit mismatch, unit change on a linked line, duplicate link (single and bulk), another company's material, allocating to another company's project, and tenant isolation of the endpoint.
Mutation check: removing the project filter from the allocation query and removing the new stock-out project check each failed the matching test; code restored and green afterwards. Frontend `tsc --noEmit` clean.

### Not verified live, and why
- The dev Postgres is stamped at Alembic revision `0004` although it already has every table up to notifications (earlier days added them by hand or with `create_all`), so `alembic upgrade head` would try to re-create tables and fail. I didn't run it. The new column still has to be added to the dev DB before the backend is restarted, or BOQ endpoints will 500. Better fix: `alembic stamp 0014` then `alembic upgrade head`.
- The process on :8000 is not this repo's backend (no `/api/v1` routes), so nothing was tested against a running server this time.

### Same day: supplier history and performance (BUILD-037 done, BUILD-038 partial)
These were marked "blocked on Purchase Orders", but POs, approval and goods receipt were all built back in Epic 8, so they were no longer blocked.
- **BUILD-037** `GET /suppliers/{id}/transactions`: every PO placed with the supplier, newest first, with project, status, ordered value, received value (qty received × PO rate), number of goods receipts and the last receipt date.
- **BUILD-038** `GET /suppliers/{id}/performance`: PO counts (total / approved-or-later / fully received / cancelled), committed value, received value, fulfilment % (received ÷ committed, over approved-or-later POs only, so a pending PO doesn't drag it down), and average lead time (PO creation to first goods receipt). **Partial:** POs have no promised delivery date, so on-time delivery can't be measured, and there is no quality or price-comparison data. The response says this in its `note` instead of showing a made-up score.
- Frontend: clicking a supplier on `/suppliers` shows its stats and PO history. This replaces the "will appear once POs are built" placeholder.
- **BUILD-039** (AI supplier insights) is still open. The data exists now; what's missing is the LLM key.
- Tests: `tests/test_supplier_history_http.py`, 5 new: an empty supplier, ordered vs received across two partial receipts, other suppliers' POs excluded, a hand-checked performance scenario (3 approved POs worth 3000, 1500 received → 50.0%; lead times 4 and 2 days → 3.0; a pending PO not counted as committed), and cross-company 404s. Mutation check: removing the supplier filter and counting pending POs as committed each failed the matching test; code restored. Frontend `tsc` clean, and `/suppliers` and `/projects` compile and serve 200 on the running dev server.
- Full suite: **112 passed**. One earlier full run had a single failure in `test_notifications_http.py::test_assigning_a_task_notifies_the_assignee`, a file untouched today. That run took 15h51m of wall-clock time, so the machine slept partway through. It passed on its own (12/12) and on a clean full rerun (112/112, 6m24s). My best guess is a token expiring during the sleep, but the traceback wasn't captured, so this is unconfirmed.

### Same day: project health score (BUILD-089, partial)
- `GET /projects/{id}/health` used to score only the schedule. Two more dimensions now come from modules that exist:
  - **Cost:** 100 − 2 × forecast overrun % (from the cost summary's earned-value-style forecast), capped to 0–100. Scored only once progress is recorded, the same gate the cost insight uses, because at 0% progress the "forecast" is just spend so far.
  - **Inventory:** the share of material-linked BOQ lines that are not over plan (from BOQ vs Actual). Unlinked lines don't count.
- `overall_score` is now the plain average of whichever dimensions have a score (it used to equal the schedule score). A new `basis` field explains each score in words, and the Overview card shows it on hover.
- **Partial:** quality, safety, labor and procurement stay null. Daily reports and attendance don't hold anything a score could honestly be built from yet.
- Tests: `tests/test_project_health_http.py`, 7 new: no data gives no scores, a hand-checked cost score (budget 1000, 50% progress, 600 spent → forecast 1200 → 20% over → 60), under budget → 100, no cost score before progress, inventory 1 of 4 over plan → 75, overall = average (schedule 80 and cost 60 → 70), and a cross-company 404. Mutation check: removing the progress gate and counting unlinked BOQ lines each broke the matching tests; code restored. Frontend `tsc` clean, `/projects` serves 200.

---

## Day 19 — 2026-10-03 — Settings (BUILD-103, 104 done; 105, 106 partial)

The previous session ended partway through a full test run after BUILD-089. That run was repeated at the start of this one: **119 passed**.

### Done
- **BUILD-103 Company settings:** `PATCH /companies/me` already existed but accepted almost anything. It now validates: name at least 2 characters, currency must be a 3-letter ISO code (`^[A-Z]{3}$`), unit system must be `metric` or `imperial`, plus length limits and a proper email. Still admin-only. New **`/settings`** page (the sidebar's "Settings" label is now a link): admins can edit, everyone else sees the values read-only.
- **BUILD-104 User settings:** `PATCH /auth/me` (own full name only; a `role` in the body is ignored) and `POST /auth/me/password` (checks the current password; new one 8–128 characters). The topbar name updates straight away through a new `updateUser` in the auth context.
- **BUILD-105 Role permissions (partial):** `GET /users` and `PATCH /users/{id}` (role, active flag), admins only, own company only (another company's user is a 404). Guards: you can't change your own role or deactivate yourself (so an admin can't lock the company out), and only a super admin can grant, change or remove super admin. Deactivation takes effect immediately, because the existing `get_current_user`, login and refresh already reject inactive users. **Why partial:** the role list on the Team section can be managed, but *what each role may do* is still a hardcoded tuple in each router (`CAN_WRITE`, `CAN_APPROVE`...). Making that editable is a real permission-system refactor, not a settings screen. There's also still no invite flow.
- **BUILD-106 Currency/unit settings (partial):** the company currency now labels every amount in the UI. `formatCurrency` reads it from a value AppShell sets when the company loads, instead of a hardcoded `PKR`, and the "Budget (PKR)" label on project create follows it too. It is a **label, not a conversion**: nothing is converted between currencies, and the page says so. The unit system is saved, but units are free text per material and nothing converts them, which is why this is partial.

### Tests: 20 new (`tests/test_settings_http.py`)
Company update and read-back; 5 invalid payloads → 422; viewer and PM → 403; settings are per company; name update (trimmed, empty rejected); a smuggled `role` in the profile update is ignored; password change (old password stops working, new one works); wrong current password → 400 and a too-short new one → 422, with the old password still valid afterwards; user list is own-company only and never includes `hashed_password`; non-admins → 403; a role change applies on the next request; a deactivated user is locked out (401 on the existing token, 403 on login); an admin can't demote or deactivate themselves; a company admin can't grant super admin; `role: null` → 422; another company's user → 404 and unaffected.
Mutation check: removing the self-lockout guard and the super-admin guard each failed its test; code restored, 20/20.

### Not verified
- The frontend dev server on :3000 was no longer running and the BuildOS backend isn't running either (and still needs the `boq_items.material_id` column, see Day 18). So `/settings` has only been type-checked (`tsc --noEmit` clean), not opened in a browser. ESLint was never configured in this repo (`next lint` asks to set it up), so no lint run.
- Changing a password doesn't revoke tokens that are already issued (JWTs are stateless here); they stay valid until they expire.
- **BUILD-107 AI settings (partial):** `/settings` gets a read-only "AI assistant" section: connected or not, provider, model, and the tool-step limit. `/ai/status` now also returns `use_fallbacks` and `max_tool_iterations` (neither is secret) and still never returns the key, not even masked. The existing test that checks this was updated to the new exact shape, and `conftest.py` now pins those two env vars the way it already pinned `LLM_MODEL`. Editing the model or key from the UI isn't built: it would mean storing an encrypted API key per company in the database, which is a security decision to make first, not a default to slip in.

### Same day: reports (BUILD-108..111)
- New `app/services/report_service.py` and `GET /reports/{projects,inventory,procurement,expenses}`. Every figure reuses the service functions the rest of the app already uses (`get_project_cost_summary`, `get_health`, `get_schedule_variance_days`, `get_total_stock_on_hand`), so a report can't disagree with the screen it summarises. It is pure arithmetic, with no estimates.
  - **Projects:** budget, committed (POs), spent (expenses), forecast, expected variance, schedule variance in days, health score, open and overdue tasks.
  - **Inventory:** on hand **now** plus ok/low/out status, and received (stock-in and goods receipts) vs issued (stock-out and allocations) **in the period**. Transfers between warehouses are counted in neither, because they don't change the company total.
  - **Procurement:** PO count and value by status, ordered vs received per supplier, material requests by status, filtered by creation date.
  - **Expenses:** grouped by project × category (uncategorized shown as such), filtered by `expense_date`, plus totals per category.
- The period is `date_from`/`date_to`, inclusive, as whole **UTC** days (except expenses, which use their plain `expense_date`); `date_from > date_to` → 400. `?format=csv` returns the row table as a CSV attachment, with commas in names quoted properly; any other format → 422. Access matches the existing financial read endpoints: any signed-in user in the company.
- Frontend: a **`/reports`** page (sidebar "Reports") with four tabs, date pickers where they apply, summary tiles, and Print and Download CSV buttons.
- **Not built:** PDF export (it would need a new dependency; Print → Save as PDF from the browser covers it for now) and **BUILD-112 AI executive report** (needs the LLM key).
- Tests: `tests/test_reports_http.py`, 9 new: the project report equals the cost summary field for field, plus the health score and task counts; inventory balances and movements with a transfer and both kinds of issue; the period filters movements but not the balance, including a row at 23:30 UTC on the last day; procurement status breakdown and per-supplier ordered vs received; a procurement period; the expense grouping and period (a June expense excluded from May); bad periods → 400; CSV quoting and 422 on an unknown format; and tenant isolation on all four reports. Mutation check: removing the tenant filter on the expense report and counting transfers as received each failed its test; code restored.

### How the new pages were checked
- `tsc --noEmit` clean. Your running :3000 dev server compiles and serves `/settings`, `/reports` and `/projects` (200).
- I tried a full browser check with a second copy of the app (backend on :8001 with a scratch SQLite DB, seeded through the API, and frontend on :3001). The backend side worked, but when the :3000 dev server came back up, both Next servers were sharing `frontend/.next` and fighting over its cache, so I stopped mine before it could corrupt yours. Pages have **not** been clicked through in a browser.
- The BuildOS backend on :8000 is now running this code against the dev Postgres, which still doesn't have `boq_items.material_id` (see Day 18). Until it's added, the BOQ tab, project health, dashboard insights and the project report will 500 there.

---

## Day 20 — 2026-10-04 — UX polish (BUILD-113..119 done, 120 partial)

### The problems this fixes
A survey of every page found three real bugs, not just polish:
1. **Failures looked like empty data.** Equipment, workforce, inventory and procurement rendered "No X yet" whenever `data` was undefined, so a slow load or a dead backend looked exactly like an empty company. The dashboard's insights card said "Checking your projects…" forever if insights failed, which is exactly what happens on the current dev DB until `boq_items.material_id` exists.
2. **Failed saves were silent.** Eleven handlers did `await mutation.mutateAsync(...)` with no error handling: nothing on screen, plus an unhandled promise rejection.
3. **422s showed "[object Object]".** FastAPI sends a list of field errors for validation failures, and `ApiError` stringified it.

### Done
- **Errors (117):** `api.ts` turns 422 details into "field: message; …". A global `MutationCache.onError` shows a toast for any failed mutation, except the 17 hooks whose pages already show the error next to the form (tagged `meta: { inlineError: true }`, so nothing is reported twice). A small `attempt()` helper stops those 11 handlers early without an unhandled rejection. Queries: shared `ErrorState` with **Try again** on every main list, the dashboard, the project page, insights and the four reports. Queries no longer retry 4xx at all, and retry 5xx/network failures once instead of three times: against a dead backend the error now shows after about 6 s instead of about 28 s (measured).
- **Loading, skeletons, empty (114–116):** `components/ui/states.tsx` provides `Skeleton`, `TableSkeleton`, `EmptyState`, `ErrorState` and `QueryView` (loading → error → empty → content), applied to equipment, workforce, inventory stock, material requests, purchase orders, projects, suppliers, documents, dashboard, insights and reports.
- **Toasts (118) and confirmations (119):** `components/feedback.tsx`, a small provider with no new dependency. Toasts: at most three, errors stay longer, `aria-live`. Confirm dialog: focuses Cancel, Escape and a backdrop click cancel, `role="alertdialog"`. Confirmations now cover deleting a document and deactivating a user (both were `window.confirm`), plus removing a BOQ line, **approving a PO** (it states the amount being committed) and approving or rejecting an AI draft (it says a real material request will be created). Removing a task dependency is easy to undo, so it has no confirmation.
- **Responsive (113):** below `md` the sidebar becomes a drawer, with a menu button, backdrop, Escape to close and auto-close on navigation. Padding shrinks, the user's name is hidden on very small screens, the search and notification dropdowns are capped to the screen width, and project/report tab rows scroll sideways.
- Small fixes found while checking: the inventory forecast card no longer says "No materials to forecast yet" while loading, and supplier names are left-aligned now that they're buttons.
- **BUILD-120 partial:** server validation is now readable everywhere, and several forms check up front (currency, password length, date range). Only project create uses zod on the client, and converting every form to react-hook-form + zod is a larger change for a later pass.

### How it was checked
- `tsc --noEmit` clean, and the backend suite is unchanged at 148 passing (no backend change today).
- **In a real browser this time**, against an isolated copy: the frontend copied to a scratch folder (to avoid sharing `.next` with the :3000 dev server) on :3001, plus a throwaway backend on :8001 with a scratch SQLite DB seeded through the API. Checked: the dashboard renders real data; at 375px the sidebar is hidden, the drawer opens, and navigating closes it; supplier history shows 60.0% received and PKR 700K committed; project health is 70/60/100 → overall 77, matching the hand calculation; BOQ vs actual shows 150 of 200 bags (−25.0%, within plan); a unit-mismatch BOQ line shows the server message inline with no duplicate toast; Remove opens the dialog and Escape keeps the line; an expense of 0 shows the toast "amount: Input should be greater than 0"; with the backend stopped, lists show the retryable error instead of "No X yet". The console had no unhandled rejections, only the expected 400/422 network entries and one `getComputedStyle` error from an injected script that isn't app code.

---

## Day 21 — 2026-10-05 — Security (BUILD-121..124, 126 done; 125 partial)

The previous session stopped partway through a test run. Nothing was lost; work picked up at BUILD-121.

### BUILD-121 API authorization
`tests/test_api_authorization_http.py` reads every operation from the OpenAPI schema (this FastAPI version, 0.141, includes routers lazily, so `app.routes` doesn't list them), fills path parameters with random UUIDs, and calls each one with **no token** and with a **forged token**. Every one of the ~120 non-public operations answered 401. The public allow-list is exactly 4 (health, register, login, refresh). A new route without auth fails this test automatically. It's written as one looping test per case rather than 240 parametrized tests, because each test resets the database and the parametrized version added about 7 minutes to the suite.

### BUILD-122 Tenant isolation, with 4 real leaks fixed
I audited every ID a client can send in a request body against the service that receives it. Fixed:
- **Task `assignee_id`** wasn't checked. Assigning a task to another company's user worked, **and sent that user a notification containing the task title and project name**. Now 404, and no notification is sent.
- **Expense `category_id`** wasn't checked, and the expense report joined categories without a company filter, so another company's category name could show up in a report. Both fixed.
- **Material `category_id`** and **equipment `current_project_id`** weren't checked. Now 404.
Tests: `tests/test_tenant_references_http.py`. Mutation check: disabling the assignee check fails the test.

### BUILD-123 Input validation
- SQLite (the test DB) ignores `VARCHAR(n)`, but Postgres rejects over-long values with an error, so **41 request fields across 12 schemas** without a `max_length` were 500s waiting to happen in production. All now have limits matching their columns, and `tests/test_schema_limits.py` compares every request schema against the column sizes, so a new field can't regress.
- Update schemas make every field optional, which also lets a client send `null`. For a NOT NULL column that was an `IntegrityError` (a 500). Verified by disabling the fix: `NOT NULL constraint failed: projects.name`. A new `app/db/updates.apply_changes()` reads nullability from the model's columns and returns 422. It replaces the copy loop in 12 services. Clearing an optional field (e.g. `client_name: null`) still works.

### BUILD-124 Upload validation
The allow-list trusted the client's Content-Type, so an executable or HTML page could be stored as a "PDF". Uploads now check the bytes: PDF/PNG/JPEG/WEBP signatures; `.docx`/`.xlsx` must be real Office zip packages (`word/document.xml` / `xl/workbook.xml`); `.doc`/`.xls` must have the OLE2 header; text/CSV must contain no NUL bytes. UTF-8 isn't required, so cp1252 CSVs from Excel still work. A mismatch is 415 and nothing is stored. The existing `.docx` test was uploading a fake zip header, so it now builds a real minimal `.docx`. No virus scanning (that would need an external service).

### BUILD-125 Rate limiting (partial)
- **Login:** 5 *failed* attempts per (IP, email) per 15 minutes, then 429 with `Retry-After`. Once locked, even the right password is refused until the window passes, otherwise the limit would tell an attacker when a guess was right. Success clears the count, and email case doesn't get around it.
- **Register:** 10 per IP per hour. **Password change:** 5 wrong current passwords per user per 15 minutes, so a stolen session can't guess the real password.
- **Why partial:** counters live in process memory (`app/core/rate_limit.py`). That's correct for today's single uvicorn process, but separate workers or containers would each count separately. Redis is in docker-compose and the limiter has a three-method interface ready to move there. It's also keyed on the client IP as uvicorn sees it, so behind a reverse proxy it needs the proxy's forwarded-IP header configured, which is a deployment (Epic 26) item.

### BUILD-126 Audit log
- `audit_log` table (migration `0016`), written in **the same transaction** as the change it describes, so it can't record something that was rolled back (tested: a refused second approval leaves no entry). Recorded: PO created/approved (with totals rounded to the cent), goods received, material request approved/rejected, AI draft approved/rejected, expense recorded, role changed, user deactivated/reactivated, company settings (only fields that actually changed, with before and after), document deleted, BOQ line deleted. No-op changes aren't logged. The inventory ledger was already append-only with `created_by`, so it isn't duplicated here.
- `GET /audit-log` (admins only, own company, filter by entity type). There are deliberately **no** update/delete endpoints, and a test asserts that. Settings shows an "Activity log" section for admins.
- Tests: `tests/test_audit_log_http.py` (7).
- Full suite: **177 passed** (it took 16 minutes on a busy machine). Frontend `tsc` clean.
- **Dev DB:** like `boq_items.material_id` (Day 18), the new `audit_log` table (migration `0016`) has to be created in the dev Postgres before the running backend is used. Every audited action writes to it, so creating or approving POs, expenses, role/settings changes and document/BOQ deletes fail until it exists.

---

## Day 22 — 2026-10-06 — Testing (BUILD-127..132 done; 133 still partial; 134 waiting on a decision)

### What was missing
Inventory, procurement and project/cost logic, the math CLAUDE.md rule 15 names explicitly, had **no dedicated tests**; they were only exercised on the side by other suites. Writing them found **6 bugs**:

**Procurement (BUILD-131), `tests/test_procurement_http.py` (16 tests):**
1. The material-request status endpoint accepted *any* status, so a request could be set to "converted" without a PO, or back to "pending". It now only approves or rejects (400 otherwise).
2. Raising a PO from an **approved** request left it "approved" (only *pending* ones were marked converted), so the normal path never closed the request, and a PO could even be raised from a **rejected** or already-converted one. Now a PO can only come from a pending or approved request (409 otherwise), and the request becomes "converted" either way. The request is checked *before* the PO is created.
- Product gap found along the way: **there was no way to approve or reject a material request in the UI**, though approvers were being notified to do it. `/procurement` now has Approve/Reject buttons for the approver roles (reject asks for confirmation).

**Projects (BUILD-132), `tests/test_projects_finance_http.py` (16 tests):**
3. A **negative budget** was accepted on update (create already refused it).
4. An **end date before the start date** was accepted, which breaks schedule variance and the Gantt. Now 422, checked on the combined values since an update may change only one date.
5. **Deleting a project that has records** returned 204 on SQLite and left orphaned expenses. On Postgres it would be a foreign-key error (a 500). It's now a 409 naming what's attached ("This project still has expenses. Set its status to cancelled instead."). The list of referencing tables comes from the model metadata, so new tables are covered automatically.
6. Related, and the root cause of #5 going unnoticed: **SQLite doesn't enforce foreign keys unless told to**, so the whole suite had been more permissive than Postgres. `conftest.py` now turns enforcement on (and a test checks it really is on). The full suite still passed with it on, so no other test was relying on a dangling reference.

**Inventory (BUILD-130), `tests/test_inventory_http.py` (10 tests):** balances as the sum of movements (including fractional quantities), insufficient stock per warehouse, exact-to-zero withdrawal, transfers as two linked rows that conserve the total, positive quantities only, allocations, dashboard low/out-of-stock counts at the boundary, history order and author, roles, tenant isolation. No bugs found.

**Unit tests (BUILD-127), `tests/test_units.py` (27):** schedule variance (behind, ahead, capped past the end, no dates, zero length, not started), the upload content check (15 cases), the rate limiter (window, `Retry-After`, independent keys) and `apply_changes`.

### Not done
- **BUILD-134 frontend tests:** the frontend has no test runner. A browser-level suite (e.g. Playwright, driving the real app against a seeded backend) is the right tool for "critical flows", but it's a new dev dependency plus browser downloads, so it needs a decision first (CLAUDE.md rule 17). Until then the flows were checked by hand in a browser on Day 20.
- **BUILD-133** stays partial: real model behaviour can't be tested without an API key.

Full suite: **219 passed** with foreign keys enforced (24 minutes on this machine), plus the 27 unit tests run separately. Frontend `tsc` clean.

---

## Day 23 — 2026-10-07 — Deployment groundwork (BUILD-137, 141 done; 135, 140, 142 partial; 136, 138, 139 need decisions)

### The most important finding: the migration chain was never proven
The dev database was built partly with `create_all` and hand-written `ALTER`s (it's stamped at revision 0004 but has every table), so nobody knew whether `alembic upgrade head` on an **empty** database, which is exactly what production will do, actually produces the schema the code expects. I checked on a **throwaway Postgres 17 cluster** (own data directory in a scratch folder, port 5499; the real dev server wasn't touched):
- 0001 → 0016 runs cleanly. A full downgrade to empty and back up also works.
- Comparing the result with the models (Alembic's `compare_metadata`) found **no missing tables, columns or wrong types**. The only differences are harmless: the migrations add `company_id` foreign keys the models don't declare (the DB is stricter), and two unique columns use a constraint instead of a unique index. Plus one real gap: **`attendance` and `employee_project_assignments` never got their `company_id` index** (every query on them filters by company). Migration **0017** adds them, and it goes up, down and up again cleanly.
- **The whole test suite then ran against that real Postgres: 256 passed** (1 skipped, the SQLite-only FK guard). `conftest.py` now takes an opt-in `TEST_DATABASE_URL` for this. The default is still SQLite, because the Postgres run takes about 50 minutes here.

### Done
- **BUILD-137 Environment configuration:** with `ENVIRONMENT=production` the backend **refuses to start** if the JWT secret is the published default or shorter than 32 characters, the database URL uses the example password, or CORS allows localhost. Development is unaffected (the dev `.env` says `development`, checked). `deploy/.env.production.example` documents every value. **`.gitignore` didn't actually cover `.env.production`**: its patterns only matched `.env` and `*.env`. It now ignores every `.env.*` except the examples (verified with `git check-ignore`) and `backups/`.
- **BUILD-141 Backups:** `deploy/backup.sh` dumps the database (`pg_dump` custom format) **and** archives uploaded files. Documents and photos live on disk, so a database dump alone isn't a backup. Each file is written under a temporary name, checked readable (`pg_restore --list` / `tar -t`), then renamed, and old ones are pruned after `KEEP_DAYS`. Restore steps are in `deploy/OPERATIONS.md`. `.gitattributes` keeps `*.sh` LF so the script works when checked out on Windows. Only syntax-checked here (`bash -n`): there's no Docker on this machine to run it against the stack.

### Partial
- **BUILD-135 Production Docker:** `backend/Dockerfile.prod` (non-root, no compiler, migrations on start, **one worker** because of the in-memory rate limiter, `--proxy-headers` trusting only `FORWARDED_ALLOW_IPS`), `frontend/Dockerfile.prod` (multi-stage, real `next build`, dev deps pruned, non-root), `.dockerignore`s, and `deploy/docker-compose.prod.yml` (no source mounts, DB/Redis not published, persistent `uploads` volume, backend healthcheck on `/health/ready`). **Not built:** Docker isn't installed here. What *was* verified: the production `next build` passes (all 17 routes, run in an isolated copy so the dev server's `.next` wasn't touched), and the migrations run on a fresh Postgres.
- **BUILD-140 CI:** `.github/workflows/ci.yml` runs the backend tests on SQLite **and** on a Postgres service, a **migration-drift check** that fails the build if the migrated schema stops matching the models (checked both ways: passes now, fails when I dropped a column), and the frontend `tsc` and `next build`. **CD** isn't set up because there's no deployment target yet. Not yet run on GitHub, since nothing has been pushed.
- **BUILD-142 Logging/monitoring:** one log line per request (`request_id method path status duration_ms`, **never the query string**), an `X-Request-ID` header on every response (an ID from a proxy is kept if it looks sane), 5xx logged at warning level, `LOG_LEVEL` setting, and a public **`/health/ready`** that checks the database and returns 503 when it's unreachable. Tests: `tests/test_ops_http.py` (5). No metrics or alerting service, since none has been chosen.

### Needs a decision
- **BUILD-136** containerised vs managed Postgres, **BUILD-138** which S3-compatible storage, **BUILD-139** domain and reverse proxy/TLS. `deploy/OPERATIONS.md` explains what each choice changes.

---

## Day 24 — 2026-10-08 — The greyed-out sidebar modules are live

Zark asked why BOQ, Tasks, Schedule, Daily Reports, Budgets, Expenses and Project Costs were greyed out. The features were already built, but only as **tabs inside each project**. The Day 1 sidebar listed them as company-wide pages that were never built, so they were shown disabled (`href: null`) rather than as dead links. That was accurate but confusing, because the work existed. All seven are now real pages:

- **Per project, with a project picker** (`components/project-scoped-page.tsx`): **BOQ**, **Schedule**, **Daily Reports**, **Project Costs**. They reuse the exact panels from the project tabs (`BoqPanel` and `CostsPanel` moved out of the project page into `components/`, which cut that page from about 640 to 332 lines). The picker remembers the last project across these pages and supports `?project=<id>` links (Budgets links rows to Project Costs this way). It reads the URL directly rather than with `useSearchParams`, which would need a Suspense boundary to pass `next build`.
- **Across all projects:**
  - **Tasks:** new `GET /tasks` (filters `mine`, `status`, `project_id`; open work first, then by due date, undated last; includes project and assignee names). Overdue tasks are flagged, and status can be changed inline. Tests: `tests/test_company_tasks_http.py` (3), plus the existing authorization sweep picked up the new route automatically.
  - **Budgets:** budget vs spent vs committed for every project, with a "% used or committed" bar and the forecast variance. It uses the same numbers as the project report and the Costs tab.
  - **Expenses:** every expense across projects, filterable by project, with a form to record one. It also adds the **first UI for expense categories**: the API supported them, but nothing could create or pick one, so every expense showed as "Uncategorized" in reports. The form appears only for roles allowed to record expenses (the API enforces this anyway).

### A real bug found while testing: dates were a day behind in the morning
Several forms defaulted their date with `new Date().toISOString().slice(0, 10)`, which is the **UTC** date. In Pakistan (UTC+5) that's yesterday until 5 am, so **attendance and daily reports defaulted to the wrong day** for early shifts (and so did the new expense form and the overdue check on Tasks). Replaced all four with `localToday()` in `lib/utils.ts`. Confirmed in the browser at 00:xx local time: the form showed 2026-10-04 while UTC was still 2026-10-03.

### Checked
In a browser against an isolated copy (frontend on :3001 in a scratch folder, throwaway backend on :8001 with seeded data; the :3000/:8000 dev servers and the dev DB untouched): every sidebar item is a link; Tasks lists across projects, flags overdue, and an inline status change re-sorts the list; BOQ switches project and shows BOQ vs actual; Schedule keeps the chosen project and shows 18 days behind (checked by hand: 50% elapsed vs 35% done over 120 days); Daily Reports and Project Costs show the right project's data; Budgets totals match; Expenses creates a category, records an expense under it and updates the total. No console errors. All seven pages also compile and serve 200 on the :3000 dev server. Frontend `tsc` clean; task-related backend suites 45/45.

---

## Day 25 — 2026-10-09 — RFQs, quotations, comparison and payments (BUILD-041..043, 054)

Built at Zark's request, after committing Days 18–24 to `claude/project-thread-onhym2`. These were previously marked as cut from scope.

### RFQ → quotations → comparison → award (BUILD-041..043)
- **RFQ:** a title, optional project, quotes-due date, materials and quantities, and the suppliers to ask. It can be raised **from a material request** (pending or approved): the project and items are copied over. Numbered `RFQ-1001…` per company.
- **Quotations:** staff enter each supplier's quote (suppliers don't log in): a rate per item, delivery days, valid-until date and notes. A quote must price **every** item exactly once, so quotes are always comparable like for like. Re-entering a supplier's quote replaces it, and the form pre-fills the existing rates. A supplier who quotes without an invitation is added to the invited list.
- **Comparison:** computed on the server (CLAUDE.md rule 11): line amounts, totals, the cheapest rate per item, the cheapest total (ties flagged for all), and expiry. Quotes are listed cheapest first.
- **Award:** drafts a **purchase order at the quoted rates** through the existing PO service, so it goes to **pending approval** like any other PO and nothing is committed without a human approving it (rule 14). The RFQ is marked awarded in the same transaction that creates the PO, so it can't be awarded twice, and if the PO can't be created (e.g. its material request was rejected meanwhile) the RFQ stays open with nothing logged. Expired quotes can't be awarded. Awarding and cancelling are logged in the audit log. Roles: purchasing roles create RFQs and enter quotes; only admins and PMs award or cancel.
- New page **/rfqs** (sidebar: Supply Chain → RFQs & Quotes).

### Payments (BUILD-054)
- **Supplier payments** against **approved** POs only (draft, pending and cancelled POs aren't owed yet). **No overpaying:** a payment that would exceed what's outstanding is refused, with the outstanding amount in the message. Every PO now reports `amount_paid` and `payment_status` (unpaid / partially paid / paid), shown in a new "Paid" column on the PO list.
- **Client receipts** per project.
- **Cash summary:** received, paid out and net, overall and per project; and **owed to each supplier** (approved PO value − paid).
- Payments are **append-only** (no edit or delete endpoints; correct a mistake by recording what actually happened) and every one goes in the audit log. Only admins and accountants record them; everyone in the company can view.
- New page **/payments** (sidebar: Cost Control → Payments).
- Migrations **0018** (rfqs, rfq_items, rfq_suppliers, quotations, quotation_items) and **0019** (supplier_payments, client_receipts). New statuses are stored as text, not Postgres enums, so adding one later needs no migration. Applied to the dev Postgres (backed up first); afterwards the schema matched the models (drift check passed).

### Found while testing in the browser
- **Rounded money hid real differences:** the compact format showed rates of 1,400 and 1,450 both as "PKR 1.4K", and totals of 1,805,000 and 1,840,000 both as "PKR 1.8M", on a page whose whole job is comparing prices. Added `formatMoney()` (exact, with thousands separators) for places where amounts are compared or confirmed: RFQ comparison, payments, and the PO list and **PO approval dialog** (which had been asking people to approve "PKR 1.8M").

### Checked
- Tests: `tests/test_rfq_http.py` (12) and `tests/test_payments_http.py` (11). These cover the hand-checked comparison (including a tie), award → pending PO at quoted rates → material request converted, expired and failed awards leaving the RFQ open, overpay refused to the cent, the cash summary hand-checked, roles and tenant isolation. Mutation check: removing the overpay guard, the expiry guard, or the approved-PO filter in the summary each failed its test; restored.
- Browser (isolated copy on :3001/:8001 with throwaway data): RFQ with two quotes compares correctly; a third quote entered through the form, from an uninvited supplier, adds them and updates the cheapest-per-item highlights; award via the confirm dialog drafts PO-1001 for 1,805,000; the PO is approved via its dialog; a 1,000,000 cheque payment updates paid, net, owed and history; an overpayment shows the inline warning and the server's refusal. No console errors except that expected 400.
- Full suite after this work: **283 passed**.

---

## Day 26 — 2026-10-10 — Searching inside documents (BUILD-076, 077 done; 080 keyword version)

Next on the AI list that doesn't need an API key: making the *contents* of uploaded documents usable. Before this, the app (and the AI assistant) only knew titles and filenames.

### Done
- **BUILD-076 Text extraction** (`app/services/document_text.py`): PDF text layer (new dependency **`pypdf`**: pure Python, BSD, no native binaries; the only way to read PDFs without one), Word `.docx` and Excel `.xlsx` (both read with the standard library: they're zip packages of XML), plain text and CSV (UTF-8, falling back to cp1252 for Excel exports). It's deliberately honest about limits: a PDF with no text layer (a scan) is marked **no text**, images and old binary `.doc`/`.xls` are **not searched**, and a file that can't be parsed is **couldn't read**. Nothing is guessed, and there's no OCR. Extraction never breaks an upload.
- **BUILD-077 Chunking:** passages of about 900 characters, broken at paragraph or sentence ends, with 150 characters of overlap so a phrase across a boundary isn't lost, keeping the **page number** for PDFs. Stored in a new `document_chunks` table (migration **0020**, which also adds `text_status`, `text_chars` and `page_count` to documents). Indexing runs on upload, `POST /documents/{id}/reindex` rebuilds one document, and `scripts/index_documents.py` catches up documents uploaded earlier (the dev DB has none yet).
- **BUILD-080 (keyword version):** `GET /documents/search?q=` returns passages containing **all** the words (case-insensitive), exact phrase first, then by how often the words appear. Results show the document, page, project and a snippet around the match. `_` in a word is escaped so it isn't a SQL wildcard. Tenant-isolated, with an optional project filter. Meaning-based search ("find clauses about delays" matching "extension of time") needs embeddings (078/079), which still wait on a provider choice, so this is marked partial.
- **For the AI assistant:** a new `search_documents` tool returns the matching passages with title and page, so once an API key is set the assistant can quote and cite your contracts and specs instead of saying it can't read files.
- **Documents page:** a "Search inside documents" box (debounced; matched words highlighted without injecting HTML; clicking a result opens the PDF **at that page**, or downloads other types) and a "Searchable" column (Yes · N pages / No text / — / Couldn't read).

### Checked
- `tests/test_document_search_http.py` (13): each format extracted (with a real multi-page PDF built in the test, plus a text-less "scan"), unsupported/failed cases, chunk size, overlap and pages, upload → search hit with the right page, all-words matching, phrase ranking, project filter, textless and image uploads still succeed, `_` treated literally, delete removes passages, reindex doesn't duplicate and is role-limited, tenant isolation, and the AI tool returning only the caller's company's passages. Mutation check: removing the `_` escaping fails the wildcard test (my first `sed` attempt didn't actually change the file, so I redid it with the editor before trusting the result).
- Browser (isolated copy, :3001/:8001): "retention money" finds page 3 of a 4-page contract with both words highlighted, and clicking it opens the PDF at `#page=3`; a Word spec is found by "concrete M25"; no matches shows a clear message; the Searchable column reads correctly for PDF, Word and a scan; no console errors.
- Dev DB migrated to 0020 (backed up first); schema matches the models.
- Full suite: **296 passed**.

---

## Day 27 — 2026-10-11 — Non-AI items: user invitations (BUILD-105)

Zark asked to carry on with the non-AI items: invitations, a faster test suite, then Playwright browser tests.

### Inviting people
Until now the only way to add a second user was inserting them directly in the database. Now:
- An admin creates an invitation (email, optional name, role) in **Settings → Invite people**. The app shows a **one-time link** (valid 7 days) to send yourself, since there's no email service configured. Only a **SHA-256 hash** of the token is stored, so the link is shown once and a database leak can't be turned into invites. Inviting the same email again replaces the old link. Pending invites can be revoked, and expired ones are flagged.
- The person opens **`/accept-invite?token=…`** (a public page). It shows which company and role they're joining, they choose a name and password (validated in the browser with zod and on the server), and they're signed straight in. The link can't be reused. If someone is already signed in on that browser, the page warns that accepting will switch accounts.
- Rules: only admins invite; only a super admin can invite a super admin; an email that already has an account anywhere is refused (emails are globally unique). Invitations are per company (another company can't see or revoke them). `user.invited`, `user.invitation_revoked` and `user.joined` go in the audit log. The two public endpoints are rate-limited per address, and the authorization sweep test's public list was updated to include exactly these two.
- **Login is now case-insensitive on email** (and registration's duplicate check too). Invited emails are stored lowercase, so `New@Example.com` would otherwise have failed to sign in.
- Migration **0021** (`invitations`, reusing the existing `user_role` type). Applied to the dev DB (backed up; drift check clean).
- Tests: `tests/test_invitations_http.py` (8): full invite → info → accept → login (any case) → link dead; the token is shown once and stored hashed; bad, expired (410) and revoked links; re-invite replaces; existing account refused; role rules; per-company; input validation.
- **BUILD-105 stays partial:** what each role is *allowed to do* is still fixed in code (each router's role list). Making that editable is a permission-system redesign, not a settings screen.

### Faster test suite
Measured first: per test, about **1 s** went on dropping and re-creating all 44 tables, and **~0.45 s per bcrypt hash or check** at cost 12 (most tests register two companies and log in). Fixes:
- The schema is built **once per run**, and each test starts by deleting every table's rows in reverse foreign-key order (works with FK enforcement on, and on Postgres).
- New setting **`BCRYPT_ROUNDS`** (default 12). The suite uses 4: same algorithm and hash format, far fewer rounds. The production config guard refuses anything below 12, with a test for that.
- Result: **305 passed in 72 s, down from ~16 minutes**, with no tests changed apart from the config test that now passes `bcrypt_rounds=12` explicitly.

### Browser tests for the critical flows (BUILD-134)
- **Playwright** (`@playwright/test`, a dev-only dependency). Locally it drives the **installed Chrome**, so no browser download; CI installs Chromium. `npm run test:e2e` in `frontend/`.
- **Fully isolated from the dev setup:** Playwright starts its own backend (`backend/scripts/e2e_server.py`: a fresh throwaway SQLite DB every run, port 8020) and its own **production build** of the frontend into **`.next-e2e`** (port 3020). That needed one config line, `distDir: process.env.NEXT_DIST_DIR || ".next"`, so a running `next dev` and the tests never share a build folder. Next.js adds the `.next-e2e` types path to `tsconfig.json` itself on build.
- **4 tests:** sign-up lands on the dashboard; wrong password refused, any-case email signs in, log out, and protected pages then bounce to login; **an admin invites someone, the invitee opens the link in a separate browser session, sees the company and role, gets the "at least 8 characters" error, then joins and is signed in; the link is then dead; the admin sees them in the team**; and **RFQ → exact totals with lowest flagged → award via confirm dialog → PO pending approval → approve via dialog (exact amount) → partial cheque payment → owed figures update → overpayment warned and refused**.
- The first run caught a real accessibility issue: Settings had **two fields both labelled "Email"** (company email and invite email), ambiguous for screen readers as well as tests. The invite fields are now "Invitee email / name / role".
- **CI:** a new `e2e` job (after backend and frontend pass) runs them on GitHub and uploads traces if anything fails.
- Result: **4 passed in 2.3 min** (including the production build).
