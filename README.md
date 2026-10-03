# BuildOS AI

AI-Native Construction ERP & Inventory Management System.

> Know What Happened. Know What's Happening. Know What's Next.

BuildOS AI connects the full construction data loop — Project → BOQ → Material Requirement →
Procurement → Purchase Order → Goods Receipt → Inventory → Consumption → Cost → Progress —
and layers AI analysis, forecasting and risk detection on top of it.

## Status

Under active development as a 21-day MVP build. See [docs/daily-log.md](docs/daily-log.md) for
day-by-day progress and [docs/tickets.md](docs/tickets.md) for the full ticket backlog (142
tickets across 26 epics).

## Stack

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query
- **Backend:** FastAPI + SQLAlchemy + Alembic + Pydantic
- **Database:** PostgreSQL
- **Cache:** Redis
- **AI:** LLM + RAG + tool-calling agents over a validated service layer
- **Deployment:** Docker Compose

See [CLAUDE.md](CLAUDE.md) for architecture rules and the AI-safety design (AI never writes to
the database directly — it always proposes, a human approves).

## Getting started

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`, health at `/api/v1/health`)
- Frontend: http://localhost:3000

That's the development setup (hot reload, source mounted into the containers). For production
(built images, migrations on start, backups) see [deploy/OPERATIONS.md](deploy/OPERATIONS.md).

## Tests

```bash
cd backend && pytest                         # SQLite, no setup
TEST_DATABASE_URL=postgresql://... pytest    # same suite on a disposable Postgres DB
cd frontend && npx tsc --noEmit && npm run build
```

CI (`.github/workflows/ci.yml`) runs all of these, plus a check that the migrations build exactly the schema the models expect.

## Repository layout

```
backend/    FastAPI app — app/api, app/core, app/db, app/models, app/schemas, app/services
frontend/   Next.js app — src/app, src/components, src/lib
docs/       Daily progress log and ticket backlog
```
