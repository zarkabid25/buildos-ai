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
