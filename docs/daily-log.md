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
