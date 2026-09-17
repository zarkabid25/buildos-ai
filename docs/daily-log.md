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
