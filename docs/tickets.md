# BuildOS AI — Ticket Backlog

Full backlog from the product plan, grouped by epic. Status legend: `[ ]` todo, `[~]` partly done (see note), `[x]` done.

## Epic 1 — Project Foundation
- [x] BUILD-001 Initialize monorepo
- [x] BUILD-002 Configure PostgreSQL
- [x] BUILD-003 Configure FastAPI
- [x] BUILD-004 Configure Next.js
- [x] BUILD-005 Authentication
- [x] BUILD-006 RBAC
- [x] BUILD-007 Company management

## Epic 2 — Dashboard
- [x] BUILD-008 Executive Dashboard
- [x] BUILD-009 Project health widget
- [~] BUILD-010 AI executive summary (dashboard summary is built from rules, clearly labelled as not AI; an LLM-written version needs an API key)

## Epic 3 — Projects
- [x] BUILD-011 Project CRUD
- [x] BUILD-012 Project dashboard
- [x] BUILD-013 Project members
- [x] BUILD-014 Project milestones
- [x] BUILD-015 Project tasks

## Epic 4 — BOQ
- [x] BUILD-016 BOQ management
- [x] BUILD-017 BOQ calculations
- [x] BUILD-018 BOQ vs Actual (material-linked BOQ lines vs stock allocated to the project; quantity variance valued at BOQ rate)
- [x] BUILD-019 AI BOQ assistant

## Epic 5 — Inventory
- [x] BUILD-020 Material categories
- [x] BUILD-021 Material CRUD
- [x] BUILD-022 Warehouse CRUD
- [x] BUILD-023 Inventory stock
- [x] BUILD-024 Stock In
- [x] BUILD-025 Stock Out
- [x] BUILD-026 Warehouse transfer
- [x] BUILD-027 Project material allocation
- [x] BUILD-028 Inventory transaction history
- [x] BUILD-029 Low-stock alerts
- [x] BUILD-030 Inventory dashboard

## Epic 6 — AI Inventory
- [x] BUILD-031 Material consumption analytics
- [x] BUILD-032 Stockout prediction
- [x] BUILD-033 AI reorder recommendation
- [x] BUILD-034 Material anomaly detection

## Epic 7 — Suppliers
- [x] BUILD-035 Supplier CRUD
- [x] BUILD-036 Supplier contacts
- [x] BUILD-037 Supplier transaction history (every PO with ordered vs received value, receipts, project)
- [~] BUILD-038 Supplier performance (fulfilment % and lead time done; on-time delivery needs a promised date on POs, and quality/price scoring needs data we don't capture yet)
- [ ] BUILD-039 AI supplier insights (PO data now exists; the model-written part needs a real LLM key, same as Epic 16)

## Epic 8 — Procurement
- [x] BUILD-040 Material request
- [ ] BUILD-041 RFQ (deferred — scope cut, see daily log)
- [ ] BUILD-042 Supplier quotation (deferred — scope cut, see daily log)
- [ ] BUILD-043 Quotation comparison (deferred — scope cut, see daily log)
- [x] BUILD-044 Purchase order
- [x] BUILD-045 PO approval
- [x] BUILD-046 Goods receipt
- [x] BUILD-047 Automatic inventory update

## Epic 9 — Finance
- [x] BUILD-048 Project budget
- [x] BUILD-049 Expense management
- [x] BUILD-050 Expense categories
- [x] BUILD-051 Project cost calculation
- [x] BUILD-052 Budget vs actual
- [x] BUILD-053 Forecast cost
- [ ] BUILD-054 Cash/payment tracking (deferred — see daily log)

## Epic 10 — AI Cost Intelligence
- [x] BUILD-055 Cost variance detection (delivered via cost-summary's `expected_variance`)
- [x] BUILD-056 Cost forecast (delivered via cost-summary's `forecast`, earned-value-style projection)
- [x] BUILD-057 Budget overrun prediction (`expected_variance > 0`, same underlying number, surfaced with red/green in the UI)
- [ ] BUILD-058 AI cost explanation ("Why is this project over budget?" needs the AI Copilot/LLM infra from Epic 16 — not built yet)

## Epic 11 — Daily Site Operations
- [x] BUILD-059 Daily report
- [x] BUILD-060 Daily report list
- [x] BUILD-061 Photo uploads (local-disk storage stand-in, not S3 — see daily log)
- [ ] BUILD-062 AI daily report generation (needs real LLM infra — not built)

## Epic 12 — Workforce
- [x] BUILD-063 Employee CRUD
- [x] BUILD-064 Project assignment
- [x] BUILD-065 Attendance
- [x] BUILD-066 Labor cost
- [x] BUILD-067 Basic productivity analytics

## Epic 13 — Equipment
- [x] BUILD-068 Equipment CRUD
- [x] BUILD-069 Project assignment (via `current_project_id`, updatable)
- [x] BUILD-070 Maintenance records
- [x] BUILD-071 Maintenance reminders

## Epic 14 — Documents
- [x] BUILD-072 Document upload
- [x] BUILD-073 Document categories
- [x] BUILD-074 Document preview/download (inline preview for PDF/images/text only; Office files download)
- [x] BUILD-075 Document metadata

## Epic 15 — AI Document Intelligence
- [ ] BUILD-076 Document text extraction
- [ ] BUILD-077 Document chunking
- [ ] BUILD-078 Embeddings
- [ ] BUILD-079 Vector storage
- [ ] BUILD-080 RAG search
- [ ] BUILD-081 Document Q&A

## Epic 16 — AI Copilot
- [~] BUILD-082 AI chat interface (built and tested with a scripted fake model; untested against the real API — no key yet)
- [x] BUILD-083 Conversation history
- [~] BUILD-084 Project-aware AI context (via project tools; no per-page context yet)
- [x] BUILD-085 Database tool calling (12 tools, read-only + draft proposals, tenant-scoped, tested)
- [~] BUILD-086 Natural language analytics (tools exist; answer quality unverified without a key)
- [~] BUILD-087 AI recommendation engine (rules-based insights + draft-and-approve are built; model-written recommendations unverified)

## Epic 17 — Project Risk
- [~] BUILD-088 Risk model (rules in app/ai/insights.py: schedule, cost, inventory, equipment, procurement)
- [~] BUILD-089 Project health score (schedule, cost and inventory scored from real data, overall = their average; quality/safety/labor/procurement have no scoring data yet)
- [x] BUILD-090 Risk dashboard (/ai-insights and dashboard card)
- [ ] BUILD-091 AI risk explanation

## Epic 18 — Scheduling
- [x] BUILD-092 Project schedule
- [x] BUILD-093 Tasks with dependencies (cycle detection included)
- [x] BUILD-094 Milestones (built Day 4; shown on the schedule timeline)
- [x] BUILD-095 Progress tracking (Project.progress_percent, built Day 3)
- [x] BUILD-096 Basic Gantt (CSS timeline bars, no drag/resize)
- [x] BUILD-097 Schedule variance (elapsed-vs-progress, in days and percent)
- [ ] BUILD-098 AI delay analysis (needs the real LLM connection from Day 14 to be tested)

## Epic 19 — Notifications
- [x] BUILD-099 Notification system (4 real triggers: task assignment, material request, PO, AI proposal)
- [x] BUILD-100 Notification center (bell dropdown in the topbar, polls every 30s)

## Epic 20 — Search
- [x] BUILD-101 Global search (case-insensitive substring, 7 entity types, topbar dropdown)
- [ ] BUILD-102 AI semantic search (needs an embeddings provider decision, see Day 14)

## Epic 21 — Settings
- [x] BUILD-103 Company settings (/settings; admins edit name/contact/currency/unit system, validated; others read-only)
- [x] BUILD-104 User settings (edit own name, change password with current-password check)
- [~] BUILD-105 Role permissions (admins list users, change roles, deactivate; guards against self-lockout and non-super-admins granting super admin. What each role may do is still hardcoded per router, not editable; no invite flow)
- [~] BUILD-106 Currency/unit settings (company currency now labels every amount in the UI, no conversion; unit system is stored but nothing converts units)
- [~] BUILD-107 AI settings (read-only section on /settings: connected or not, provider, model, tool-step limit; the key stays a server env var and is never shown. Editing model/key in the UI would mean storing an encrypted secret per company, which needs a decision)

## Epic 22 — Reports
- [x] BUILD-108 Project report (/reports: budget, committed, spent, forecast, variance, schedule, health, open/overdue tasks per project; CSV)
- [x] BUILD-109 Inventory report (current on-hand + status, received/issued in a period; CSV)
- [x] BUILD-110 Procurement report (POs by status, spend per supplier, material requests by status, in a period; CSV)
- [x] BUILD-111 Expense report (by project x category in a period, category totals; CSV)
- [ ] BUILD-112 AI executive report

## Epic 23 — UX Polish
- [x] BUILD-113 Responsive layout (sidebar becomes a drawer below md; tables scroll inside their cards; tab rows scroll; checked at 375px)
- [x] BUILD-114 Loading states
- [x] BUILD-115 Skeleton loaders (main lists, dashboard, project page, reports)
- [x] BUILD-116 Empty states (shared EmptyState; no longer shown while loading or on error)
- [x] BUILD-117 Error states (load failures show a retryable error instead of "no data"; every failed save is reported; 422s are readable)
- [x] BUILD-118 Toast notifications (no new dependency)
- [x] BUILD-119 Confirmation dialogs (delete document, remove BOQ line, approve PO, approve/reject AI draft, deactivate user)
- [~] BUILD-120 Form validation (server validation errors are now shown field by field, and a few forms check up front; only project create uses zod on the client)

## Epic 24 — Security
- [x] BUILD-121 API authorization (test walks every endpoint in the OpenAPI schema: all but 4 public ones reject no-token and forged-token requests)
- [x] BUILD-122 Tenant isolation (audit of every client-sent ID; fixed task assignee, expense category, material category, equipment project, expense-report category join)
- [x] BUILD-123 Input validation (string limits match DB columns, enforced by a test; null for a required field is a 422, not a 500)
- [x] BUILD-124 File upload validation (type allow-list, size cap, safe filenames, and file contents must match the declared type)
- [~] BUILD-125 Rate limiting (login, register and password change are limited; the counters live in process memory, so they would need Redis once there is more than one worker)
- [x] BUILD-126 Audit log (PO created/approved, goods received, material request decided, AI draft decided, expense, role/deactivation, company settings, document and BOQ deletes; admins read it in Settings)

## Epic 25 — Testing
- [x] BUILD-127 Backend unit tests (tests/test_units.py: schedule variance, upload content check, rate limiter, apply_changes)
- [x] BUILD-128 API integration tests (every module has an HTTP suite through real JWT auth; SQLite now enforces foreign keys like Postgres)
- [x] BUILD-129 Authentication tests (test_auth_http.py, test_api_authorization_http.py, test_rate_limit_http.py; role checks live with each module)
- [x] BUILD-130 Inventory tests (test_inventory_http.py: ledger math, guards, roles, isolation)
- [x] BUILD-131 Procurement tests (test_procurement_http.py; found and fixed 2 bugs in material request status handling)
- [x] BUILD-132 Project tests (test_projects_finance_http.py; found and fixed 3 bugs: negative budget on update, end before start, deleting a project with records)
- [~] BUILD-133 AI tests (tool loop, scoping, approval gate, request shape: done; real model behaviour: not testable without a key)
- [ ] BUILD-134 Frontend critical-flow tests (needs a browser test runner, e.g. Playwright, which would be a new dev dependency; waiting on a decision)

## Epic 26 — Deployment
- [~] BUILD-135 Production Docker setup (Dockerfile.prod for both apps + deploy/docker-compose.prod.yml; production `next build` and migrations verified, but no Docker on this machine, so the images themselves have not been built)
- [ ] BUILD-136 Production database (needs a decision: containerised Postgres as in the compose file, or a managed service. Migration chain verified on a fresh Postgres 17)
- [x] BUILD-137 Environment configuration (refuses to start in production with default secret / example DB password / localhost CORS; deploy/.env.production.example; .gitignore now covers every .env.* file)
- [ ] BUILD-138 Storage configuration (needs a decision on an S3-compatible provider; uploads currently go to a persistent Docker volume)
- [ ] BUILD-139 Domain/SSL (needs a domain and a choice of reverse proxy; see deploy/OPERATIONS.md)
- [~] BUILD-140 CI/CD (CI done: .github/workflows/ci.yml runs tests on SQLite and Postgres, a migration-drift check, tsc and next build. CD waits on a deployment target)
- [x] BUILD-141 Database backup (deploy/backup.sh: database + uploaded files, verified, rotated; restore steps in deploy/OPERATIONS.md)
- [~] BUILD-142 Logging/monitoring (request logs with X-Request-ID, /health/ready readiness check; no metrics/alerting service chosen)
