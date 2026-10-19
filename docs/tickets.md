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
- [x] BUILD-041 RFQ (from scratch or from a material request; invite suppliers; /rfqs)
- [x] BUILD-042 Supplier quotation (staff enter each supplier's rates, delivery and validity; re-entering replaces)
- [x] BUILD-043 Quotation comparison (side by side, cheapest per item and overall; award drafts a PO that still needs approval)
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
- [x] BUILD-054 Cash/payment tracking (supplier payments against approved POs with no overpaying, client receipts, cash by project, payables per supplier; /payments)

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
- [x] BUILD-076 Document text extraction (PDF text layer, .docx, .xlsx, .txt, .csv; scans/images reported as not searchable; no OCR)
- [x] BUILD-077 Document chunking (~900-char passages on paragraph/sentence breaks, 150-char overlap, page numbers kept)
- [ ] BUILD-078 Embeddings
- [ ] BUILD-079 Vector storage
- [~] BUILD-080 RAG search (keyword search over passages works, in the UI and as an AI tool; meaning-based retrieval waits on embeddings, 078/079)
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
- [~] BUILD-105 Role permissions (admins invite people by one-time link with a role, change roles, deactivate; self-lockout and super-admin guards. What each role may do is still fixed in code, not editable)
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
- [x] BUILD-134 Frontend critical-flow tests (Playwright: sign-up, sign-in/out, invite → join, RFQ → award → PO approval → payment; own backend + build; in CI)

## Epic 27 — Platform Super Admin (BuildOS AI 2.0)

Per `docs/design-system.md` (BuildOS AI 2.0 global UI/UX instructions). A separate, non-tenant interface for BuildOS's own staff, built out incrementally.

- [x] BUILD-143 Platform admin auth (separate `platform_admins` table/login/JWT, distinct token type so tenant and platform tokens can never be used on each other's routes; no self-registration, only `scripts/create_platform_admin.py`)
- [x] BUILD-144 Company management (list/search/view every tenant, user counts; suspend/reactivate — suspending blocks new logins and invalidates existing sessions immediately)
- [x] BUILD-145 Business dashboard (active/suspended companies, total users, new companies in 30 days — real numbers only; MRR/leads/supplier-verification counts shown as not-yet-available, not fabricated)
- [x] PLAT-006 Platform staff roles (owner/admin/support on `platform_admins.role`; owner manages staff, admin manages companies, support is read-only)
- [x] PLAT-007 Protected `/platform-admin` layout (per-page auth guard + shell, same pattern as the tenant app)
- [x] PLAT-008 Platform dashboard, company directory, company detail (extended from BUILD-144/145 with onboarding status)
- [x] PLAT-009 Company onboarding status + approve/suspend with audit history (`companies.onboarding_status`, new `platform_audit_log` table; does not gate tenant login)
- [x] PLAT-010 Staff invitations and role management (`platform_invitations`, mirrors the tenant invite flow; owner-only)
- [x] PLAT-011 CRM organizations and contacts (`crm_organizations`/`crm_contacts`; distinct from tenant `Company` until converted)
- [x] PLAT-012 Lead creation, assignment, two pipelines (SaaS sales / supplier acquisition), lead source tracking
- [x] PLAT-013 Deal Kanban + list views (`/platform-admin/crm`, stage-column Kanban with a per-card stage selector, no drag-and-drop library added)
- [x] PLAT-014 Calls/meetings/notes/reminders (`crm_activities`) + follow-up dashboard (`/platform-admin/crm/follow-ups`, open dated tasks, soonest due first)
- [x] PLAT-015 Convert lead to company onboarding (idempotent; either creates a new `Company` or links an authorized-confirmed existing one — never both, never silently double-creates)
- [x] BUILD-146 CRM leads and pipeline (superseded by PLAT-011..015 above)
- [x] PLAT-016 Global marketplace supplier registry (`marketplace_suppliers`, cross-tenant, separate from the existing per-company `Supplier` model which is untouched)
- [x] PLAT-017 Admin-led supplier onboarding (platform staff create/edit; no supplier login yet, by design)
- [x] PLAT-018 Supplier contacts, documents and verification workflow (pending → verified/rejected → suspended, enforced state machine, audit-logged)
- [x] PLAT-019 Marketplace product catalog (`marketplace_products`: price, minimum order quantity, lead time) + supplier categories and delivery coverage area tags
- [x] PLAT-020 Supplier search/filtering, supplier activity history, and future-integration groundwork (`marketplace_company_supplier_links`, `marketplace_material_mappings` — created, not yet read by anything)
- [x] BUILD-147 Supplier management and verification (superseded by PLAT-016..020 above)
- [x] PLAT-021 Supplier discovery (company-facing `/marketplace`: directory, search/category/area filters, detail, verified-only, product catalog, connect action)
- [x] PLAT-022 Company-supplier relationships (`marketplace_company_supplier_links.erp_supplier_id`; link an existing ERP supplier or create one through the existing `supplier_service`; duplicate connection refused; preferred flag; per-company status)
- [x] PLAT-023 Marketplace RFQs (`marketplace_rfq_invitations`; invites reuse the real `RfqSupplier`/RFQ flow; platform staff can assist; unauthorized/duplicate invitations refused; a suspended supplier can't be invited)
- [x] PLAT-024 Quotation comparison (platform staff may enter a quotation on a connected supplier's behalf through the existing `rfq_service.record_quotation`; existing comparison/lowest-offer logic untouched)
- [x] PLAT-025 ERP purchase-order integration (selecting a quotation is the existing `award` endpoint — no second PO system; approval still mandatory)
- [x] PLAT-026 Goods receipt synchronization (`marketplace_delivery_reports`: an idempotent, inert log of a supplier-claimed delivery; real stock only ever moves through the existing `procurement_service.create_goods_receipt`; a read-only marketplace order-status view derived from real PO/receipt data)
- [x] PLAT-027 Platform-assisted supplier matching (deterministic: material-category match or an explicit `marketplace_material_mappings` row, verified suppliers only, real price/lead-time/min-qty — never a fabricated score)
- [x] BUILD-148 Marketplace activity (superseded by PLAT-021..027 above; full two-way marketplace order sync still needs supplier-side login/portal, deliberately out of scope here)

### Phase 4.1 — Marketplace Integration Polish
- [x] Task 1: Marketplace RFQ UI (extends the existing `/rfqs` detail page: share with connected suppliers, invitation status table, quotation attribution shown inline in the comparison table — no redesign, same Card/Button/table conventions)
- [x] Task 2: Platform Admin Matching UI (`/platform-admin/marketplace/match`: company → open RFQ → material → real matching suppliers with an Invite action; Linear/Attio/Stripe-styled per the platform admin theme)
- [x] Task 3: Quotation audit attribution (`marketplace_quotation_attributions`, additive and insert-only; `Quotation.created_by_id` untouched and still correctly means "the RFQ's own creator"; a re-quote adds a new row rather than editing the old one)
- [x] Task 4: Marketplace feature flag (`companies.marketplace_enabled`, disabled by default including every pre-existing company; owner/admin-only toggle; enforced server-side at every marketplace *action* endpoint; platform administration and historical records unaffected either way)
### Phase 5 — SaaS Subscriptions & Billing
- [x] PLAT-028 Subscription plans and entitlements (`SubscriptionPlan`/`PlanPrice`, versioned pricing, configurable limits, never hardcoded in frontend)
- [x] PLAT-029 Subscription lifecycle (`CompanySubscription`, explicit state machine, DB-level partial-unique-index guard against concurrent duplicate active subscriptions)
- [x] PLAT-030 Invoices and manual payments (`SubscriptionInvoice`/`InvoiceLineItem`/`PaymentSubmission`, Decimal totals, private payment-proof storage, staff verify/reject, duplicate verification refused)
- [x] PLAT-031 Renewal, grace period and access control (`SubscriptionEvent` history, backend-enforced entitlement guards on project/team-member creation, billing status surfaced on `/billing`)
- [x] PLAT-032 Legacy company protection (`CompanyLegacyEntitlement`, data-migration-granted to every pre-Phase-5 company; `marketplace_enabled` flag preserved and untouched)
- [x] BUILD-149 Subscription management (superseded by PLAT-028..032 above)

### Phase 5.1 — Complete Billing Operations UI
- [x] Task 1: Company Subscriptions (`/platform-admin/billing/subscriptions` directory with search/plan/status filters; `[companyId]` detail with plan history, legacy-entitlement indicator, activity timeline, and grace-period/expire actions)
- [x] Task 2: Invoice Management (`/platform-admin/billing/invoices`: platform-wide list, company/status/date filters, inline line-items and payment history)
- [x] Task 3: Revenue Dashboard (`/platform-admin/billing/revenue`: MRR computed from ACTIVE subscriptions only, cash collected, outstanding balance, monthly trend from real paid invoices, plan distribution)
- [x] Task 4: Subscription Activity History (rendered on the company detail page from real `SubscriptionEvent` rows; no fabricated events)
- [x] Task 5: Company Renewal UI (`/billing` "Request renewal invoice" action; idempotent `POST /billing/subscriptions/{id}/renew`, verified to never create a duplicate invoice on repeated requests)
- [x] Task 6: Financial and compatibility tests (+8 in `test_billing_http.py`: directory/filter coverage, new companies never auto-grandfathered, MRR excludes non-active subscriptions, renewal idempotency before and after activation)
### Phase 6 — Marketplace Commissions & Revenue Management
- [x] PLAT-033 Supplier commission agreements (`supplier_commission_agreements`: percentage/fixed-fee, versioned like `PlanPrice`, one active agreement per supplier enforced by a partial unique index, date-bounded expiration)
- [x] PLAT-034 Commission ledger (`commission_ledger_entries`, append-only; `MarketplacePoAttribution` is the single source of truth for commission-eligibility, written once at RFQ award time; accrual triggers only on a real `SupplierPayment`, never on PO/goods-receipt value; partial-unique-index idempotency against duplicate accrual)
- [x] PLAT-035 Commission invoices and payments (`commission_invoices`/`commission_payments`, separate `COMM-xxxxx` numbering from SaaS billing's `INV-xxxxx`; partial settlement; unique-per-ledger-entry billing guard)
- [x] PLAT-036 Disputes and adjustments (`commission_disputes`; approval posts a new reversal entry via `commission_service.reverse_entry`, never edits the original; standalone adjustments supported separately)
- [x] PLAT-037 Revenue dashboard (`/platform-admin/commissions/revenue`: earned/invoiced/collected/outstanding kept distinct; marketplace order value reported separately, never counted as commission revenue)
- [x] BUILD-150 Commission tracking (superseded by PLAT-033..037 above)

### Phase 7 — Supplier Self-Service Portal
- [x] PLAT-038 Supplier authentication and memberships (`SupplierUser`/`SupplierMembership`/`SupplierInvitation`; a third, independent `supplier_access`/`supplier_refresh` JWT system; explicit active-supplier selection via a dedicated `select-supplier` endpoint; owner/admin/staff roles; suspend/revoke/reinstate)
- [x] PLAT-039 Supplier dashboard and profile (`/supplier-portal`, `/supplier-portal/profile`; legal name/verification status never supplier-editable, staff approval workflow preserved)
- [x] PLAT-040 Product catalog management (`/supplier-portal/products` + `/new` + `/[id]`; reuses the existing `MarketplaceProduct` table/service, ownership-enforced)
- [x] PLAT-041 RFQ inbox and quotations (`/supplier-portal/rfqs` + `/[id]`, `/supplier-portal/quotations`; reuses `rfq_service.record_quotation` via the same actor-substitution trick as platform-staff-assisted quotes; real `MarketplaceQuotationAttribution` with `method="supplier_self_submitted"`, never attributed to staff)
- [x] PLAT-042 Orders, delivery and commission statements (`/supplier-portal/orders` + `/[id]`, `/supplier-portal/commissions` + invoice detail; delivery updates reuse `MarketplaceDeliveryReport`, confirmed to never post stock; commission statement is read-only and reuses the Phase 6 commission services, fully isolated per supplier)
- [ ] BUILD-151 Payments and invoices (platform-level, i.e. BuildOS billing its own customers — distinct from the existing tenant-level `payments` module)
- [x] BUILD-152 Support tickets (superseded by PLAT-046 below)
- [ ] BUILD-153 AI business intelligence

### Phase 8 — Public SaaS Website, Onboarding & Support
- [x] PLAT-043 Public website (`/`, `/features`, `/construction-erp`, `/supplier-network`, `/pricing`, `/about`, `/contact`; dark-navy premium theme, sitemap.xml/robots.txt, per-page SEO metadata; `/marketplace` renamed to `/supplier-network` for the public page since the authenticated ERP route already owns `/marketplace`)
- [x] PLAT-044 Company registration and demo requests (`/register` reused unmodified; `/request-demo` creates/reuses a real `CrmOrganization` lead, never duplicated, with 24h duplicate-submission protection; new companies confirmed never grandfathered)
- [x] PLAT-045 Supplier application (`/become-a-supplier`; new `SupplierApplication` pending-review table; approval reuses the existing unmodified `marketplace_supplier_service.create_supplier`, resulting supplier always still PENDING verification — never auto-verified, confirmed live)
- [x] PLAT-046 Support desk (`/support`+`/[id]`, `/supplier-portal/support`+`/[id]`, `/platform-admin/support`+`/[id]`; one `SupportTicket`/`SupportTicketMessage` schema for both requester types; internal staff notes filtered server-side, never exposed externally; full company/supplier isolation; staff actions audited)
- [x] PLAT-047 Onboarding and notifications (two new `NotificationType` values added to the existing tenant `Notification` table via additive `ALTER TYPE`; new `PlatformNotification`/`SupplierNotification` tables for the two actor types with no prior notification concept; `email_service.send_email` honestly records `NOT_CONFIGURED` rather than pretending delivery)

## Epic 26 — Deployment
- [~] BUILD-135 Production Docker setup (Dockerfile.prod for both apps + deploy/docker-compose.prod.yml; production `next build` and migrations verified, but no Docker on this machine, so the images themselves have not been built)
- [ ] BUILD-136 Production database (needs a decision: containerised Postgres as in the compose file, or a managed service. Migration chain verified on a fresh Postgres 17)
- [x] BUILD-137 Environment configuration (refuses to start in production with default secret / example DB password / localhost CORS; deploy/.env.production.example; .gitignore now covers every .env.* file)
- [ ] BUILD-138 Storage configuration (needs a decision on an S3-compatible provider; uploads currently go to a persistent Docker volume)
- [ ] BUILD-139 Domain/SSL (needs a domain and a choice of reverse proxy; see deploy/OPERATIONS.md)
- [~] BUILD-140 CI/CD (CI done: .github/workflows/ci.yml runs tests on SQLite and Postgres, a migration-drift check, tsc and next build. CD waits on a deployment target)
- [x] BUILD-141 Database backup (deploy/backup.sh: database + uploaded files, verified, rotated; restore steps in deploy/OPERATIONS.md)
- [~] BUILD-142 Logging/monitoring (request logs with X-Request-ID, /health/ready readiness check; no metrics/alerting service chosen)
