# BuildOS AI

## Product
AI-native Construction ERP & Inventory Management System.
Positioning: "Know What Happened. Know What's Happening. Know What's Next."

## Architecture

Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query
Backend: FastAPI + Python + SQLAlchemy + Alembic + Pydantic
Database: PostgreSQL
Cache: Redis
AI: LLM API + RAG + AI Agents (tool-calling over a service layer, never direct DB access)
Storage: S3-compatible object storage
Deployment: Docker Compose

## Repository layout

```
backend/    FastAPI app (app/api, app/core, app/models, app/schemas, app/services, app/db)
frontend/   Next.js app (src/app, src/components, src/lib)
docs/       Daily progress logs, architecture notes
```

## Rules

1. Never modify database schema without a migration (Alembic).
2. Never bypass API validation.
3. Never put business logic inside React components — components call the API layer only.
4. Use a service layer in FastAPI (app/services) — routers stay thin.
5. Use Pydantic schemas for all request/response bodies.
6. Use TypeScript strict mode.
7. Use reusable UI components (shadcn/ui primitives, shared layout components).
8. Never duplicate API logic — one service function per business operation.
9. Every tenant-owned record must contain `company_id`.
10. Every API endpoint must enforce tenant isolation (filter by the authenticated user's company_id).
11. Financial calculations must be deterministic — no LLM-computed totals.
12. AI recommendations must never silently execute financial or inventory transactions — always draft + human approval.
13. AI-generated construction quantities (BOQ, forecasts) must be clearly marked as estimates requiring professional review.
14. Use approval workflows for important actions (PO approval, budget changes).
15. Write tests for critical business logic (inventory math, cost calculations, tenant isolation).
16. Keep UI professional and minimal — see design system in docs/design-system.md.
17. Do not add dependencies without justification.
18. Do not create unnecessary abstractions — three similar lines beats a premature abstraction.

## AI safety architecture

Never let the LLM directly manipulate the database.

```
User -> AI -> Tool -> Validation -> Business Service -> Database
```

AI proposes (draft PO, draft material request, draft report). A human approves before anything is persisted as a committed transaction.

## Design system

- Background #F7F8FA, Surface #FFFFFF, Sidebar #111827, Primary #2563EB
- Success #16A34A, Warning #F59E0B, Danger #DC2626
- Text #111827, Muted #6B7280, Border #E5E7EB
- Dark charcoal sidebar, light content area, one strong accent color, rounded cards, thin borders, minimal shadows.

## Ticket workflow

For every BUILD-xxx ticket: implementation plan -> affected files -> backend -> DB migration -> API -> frontend -> validation -> tests -> run tests -> fix -> update docs/daily log.
