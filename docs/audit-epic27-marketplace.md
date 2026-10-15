# Technical Audit — Pre-Implementation (Epic 27 continuation: CRM / Marketplace / Supplier Portal)

Audit only. No code was modified in this pass. Baseline recorded 2026-10-15.

## 0. Baseline

- Backend: `pytest` → **320 passed, 0 failed** (8 pre-existing `StarletteDeprecationWarning`s, unrelated to this audit — `HTTP_422_UNPROCESSABLE_ENTITY` naming, not a functional issue).
- Frontend: `tsc --noEmit` → clean.
- Dev Postgres: Alembic head **0022**, schema verified drift-free against the models (`compare_metadata`) on 2026-10-15.
- These are real, just-run results, not assumed from the daily log.

## 1. Actual architecture and model inventory

**Stack** (matches `CLAUDE.md`/`PROJECT_GUIDE.md`, verified against code): FastAPI + SQLAlchemy + Alembic + Pydantic backend; Next.js 14 App Router + TypeScript + Tailwind + TanStack Query frontend; PostgreSQL; Anthropic Claude via official SDK for AI; no Redis/S3 wired up yet despite being named in the architecture doc (rate limiting is in-process memory, file storage is local disk — both explicitly flagged as known limits in `PROJECT_GUIDE.md` §8).

**Auth, roles, tenancy** (`app/models/user.py`, `app/models/company.py`, `app/api/deps.py`):
- `User.company_id` is `nullable=False` — every user belongs to exactly one tenant company. `UserRole` enum: `super_admin, company_admin, project_manager, site_engineer, storekeeper, accountant, viewer`. **`super_admin` here is tenant-scoped** — a company's own top admin, not a cross-tenant role.
- `get_current_user` (deps.py) decodes a JWT with `type: "access"`, loads the `User`, and now (added 2026-10-15) also checks `user.company.is_active`.
- **Separate from this**: `PlatformAdmin` (`app/models/platform_admin.py`, added 2026-10-15, migration 0022) — no `company_id` at all, its own JWT types (`platform_access`/`platform_refresh`), its own `get_current_platform_admin` dependency, own router prefix `/api/v1/platform/*`. Verified by direct test (`tests/test_platform_http.py`) that a tenant token 401s on platform routes and vice versa. This is the only existing "sees across tenants" surface in the app.
- Tenant isolation pattern, used uniformly: every tenant table inherits `TenantBase` (`company_id` column, indexed, non-null); every service function takes `company_id` as an explicit parameter and filters by it; routers never let the client supply `company_id` — it always comes from the authenticated user/token. BUILD-122's audit (per tickets.md) already walked every client-sent ID across the app for cross-tenant reference bugs.

**Supplier / procurement chain — the critical finding for this audit:**
- `Supplier` (`app/models/supplier.py`) is `TenantBase` — i.e. **each construction company has its own private supplier directory**. A `Supplier` row has no login, no email-verified account, nothing. `SupplierContact` is just a named contact person, also company-scoped.
- `Quotation` model's own docstring states it plainly: *"Entered by staff; suppliers don't log in."* Quotations today are staff keying in a supplier's quoted price after a phone call/email — there is no supplier-side submission flow at all.
- `Rfq` → `RfqSupplier` (invited suppliers) → `Quotation`/`QuotationItem` (staff-entered prices) → award drafts a `PurchaseOrder` (needs separate approval) → `GoodsReceipt`/`GoodsReceiptItem` (receiving, feeds `InventoryTransaction`). All of this is `TenantBase`-scoped and keyed off the company's own `Supplier` rows.
- **Implication**: there is currently *no* shared, cross-tenant "marketplace supplier" concept anywhere in the schema. Building the Supplier Portal (BuildOS AI 2.0 Portal 3) or platform-level supplier verification/marketplace activity (Epic 27's BUILD-147/148) is not an extension of the existing `Supplier` table — it is a **new, parallel entity** (a supplier organization with its own login, shared across every construction company that connects with it), analogous to how `PlatformAdmin` was built separate from `User` rather than bolted onto it.

**Finance** (`app/models/payment.py`, `app/services/payment_service.py`, `app/services/finance_service.py`): `SupplierPayment` (against an approved PO, cannot overpay — enforced in service, not just UI) and `ClientReceipt`. These are **tenant-level** payments (a construction company paying its supplier / being paid by its client) — a separate concept from what Epic 27's BUILD-151 would need (BuildOS billing its own tenant customers for their subscription). No subscription/plan/billing model exists yet anywhere.

**Full current model list** (`app/models/__init__.py`, 2026-10-15): `Company, User, Project, ProjectMember, Milestone, Task, TaskDependency, BoqItem, Supplier, SupplierContact, MaterialRequest, MaterialRequestItem, PurchaseOrder, PurchaseOrderItem, GoodsReceipt, GoodsReceiptItem, ExpenseCategory, Expense, Employee, EmployeeProjectAssignment, Attendance, Equipment, EquipmentMaintenance, DailyReport, DailyReportPhoto, Document, DocumentChunk, AiConversation, AiMessage, AiProposal, Notification, MaterialCategory, Material, Warehouse, InventoryTransaction, AuditLog, Rfq, RfqItem, RfqSupplier, Quotation, QuotationItem, ClientReceipt, SupplierPayment, Invitation, PlatformAdmin`. Nothing resembling a CRM lead/deal, a subscription/plan, a marketplace order, or a commission exists.

**AI boundary** (`app/ai/tools.py`, `app/ai/copilot.py`): every tool function takes `ToolContext` carrying `company_id` from the authenticated user; `company_id` is **never** part of a tool's JSON-schema input, so the model cannot request another tenant's data even if it tried. Tools are read-only except `propose_material_request`, which only ever creates a draft `AiProposal` — committed only via `ai_proposal_service.approve_proposal`, run as the *approving human user*, not the AI. This boundary is unaffected by anything in Epic 27 so far and should stay the pattern for any future AI-touching marketplace feature (e.g. an AI-assisted RFQ-to-supplier matcher would still need to go through a draft+approve gate).

## 2. Reusable services and endpoints

Directly reusable patterns (not reusable code per se, since each is tenant-scoped, but the *pattern* generalizes):
- `platform_company_service.py` / `platform_auth_service.py` / `app/api/v1/platform.py` — the exact template for any new platform-level service: explicit `db.query(...)` with no implicit tenant filter (by design, since this is the one cross-tenant surface), its own Pydantic schemas in `app/schemas/platform.py`.
- `rfq_service.py` + `procurement_service.py` — the award-drafts-a-PO flow (`rfq_service`'s award calls into `procurement_service.create_purchase_order`) is the right shape to imitate for "marketplace RFQ → quotation → order" later, just with a cross-tenant supplier identity instead of a company-owned one.
- `notification_service.py` — 4 existing triggers (task assignment, material request, PO, AI proposal); a 5th trigger ("a marketplace supplier submitted a quotation") would slot into the same table/pattern.
- `audit_service.py` — already logs PO approval, goods receipt, role changes, etc.; platform-level actions (suspend/reactivate company) do **not** currently write to this audit log — see risk below.

Existing endpoints a new marketplace module would sit beside, not replace: `/api/v1/suppliers`, `/api/v1/rfqs`, `/api/v1/procurement/*`, `/api/v1/payments` (all tenant-scoped, unaffected by this plan).

## 3. New module directory proposal (additive only)

```
backend/app/models/
  marketplace_supplier.py   # new: supplier org + login, NOT TenantBase
  crm.py                    # new: Lead, Contact, Deal, PipelineStage, Activity (platform-owned, not tenant-owned)
backend/app/services/
  marketplace_supplier_auth_service.py   # mirrors platform_auth_service.py's pattern: own JWT type "supplier_access"
  marketplace_supplier_service.py
  crm_service.py
backend/app/schemas/
  marketplace_supplier.py
  crm.py
backend/app/api/v1/
  marketplace_suppliers.py   # prefix /api/v1/suppliers-portal/* or similar, public login only
  platform_crm.py            # prefix /api/v1/platform/crm/*, platform-admin only
frontend/src/app/
  supplier-portal/           # new portal root, own shell (mirrors platform-admin/)
  platform-admin/crm/        # new pages under the existing platform-admin tree
frontend/src/lib/
  supplier-auth-store.ts, supplier-api.ts, supplier-auth-context.tsx   # third parallel auth stack
  use-crm.ts
```

This follows the project's own established pattern: Day 28 built a fully parallel auth stack for `PlatformAdmin` rather than reusing `User`'s; the same reasoning applies to a marketplace supplier identity, which also doesn't belong to one tenant.

## 4. Additive database migration plan

Proposed as **two independent migrations** (CRM has no dependency on the supplier model), each additive-only, no renames/drops of existing tables:

- `0023_crm.py`: `leads` (company name, contact info, pipeline_stage, source, owner_platform_admin_id, timestamps), `crm_activities` (lead_id, type, note, created_by). No FK to any existing tenant table — leads are prospects, not yet `Company` rows.
- `0024_marketplace_suppliers.py`: `marketplace_suppliers` (own login: email/hashed_password/name, verification_status, no company_id — mirrors `platform_admins`), `marketplace_supplier_contacts`. Later migrations (not in this pass) would add RFQ/quotation tables that reference `marketplace_suppliers.id` instead of (or alongside) the existing tenant-owned `suppliers.id`.

Both follow the existing hand-written-migration convention (no live autogenerate target in CI beyond the drift check) and would be applied to the dev Postgres with `alembic upgrade head`, then drift-checked with the same `compare_metadata` script already used on 2026-10-15 — same discipline as Day 28, not assumed to be clean without running it.

## 5. API integration contract (proposed, not built)

- `POST /api/v1/platform/crm/leads`, `GET /api/v1/platform/crm/leads`, `PATCH /api/v1/platform/crm/leads/{id}` — platform-admin only, via existing `get_current_platform_admin`.
- `POST /api/v1/supplier-portal/auth/login|refresh|me` — new, public login endpoint (added to `test_api_authorization_http.py`'s public allow-list the same way the two platform auth routes were).
- `GET /api/v1/supplier-portal/rfqs` (RFQs this supplier was invited to, across whichever companies invited them) — this is the first genuinely new cross-tenant *read* pattern: a marketplace supplier's view spans multiple companies' RFQs by design, which is different from everything in the app so far except the platform-admin company list. Needs its own explicit isolation tests (a supplier must see only RFQs they were actually invited to, never another supplier's).

## 6. Security / compatibility risks

1. **A third identity type compounds the "which token am I" surface.** Tenant (`access`/`refresh`), platform (`platform_access`/`platform_refresh`), and a prospective supplier (`supplier_access`/`supplier_refresh`) token must all be mutually rejected on each other's routes, the same way `test_platform_http.py` verifies today. This needs the same direct test for the third type before shipping it, not an assumption that the pattern "just works."
2. **Platform actions aren't in the audit log.** `platform_company_service.set_company_suspended` doesn't write an `AuditLog` entry — every other consequential action in the app does (PO approval, role changes, company settings edits). This is a real gap introduced on Day 28, not something this audit is inventing; worth fixing before more platform-admin actions are added, so there's a record of *which platform admin* suspended *which company and when*.
3. **Marketplace RFQ visibility across tenants is a new category of isolation bug risk.** Every existing isolation bug found and fixed in this project (BUILD-122) was "company A shouldn't see company B's data." A marketplace supplier *legitimately* spans multiple companies — the bug risk flips to "supplier X shouldn't see RFQs belonging to a company that never invited them," which needs new, explicit tests, not reuse of the existing company-isolation test suite's assumptions.
4. **`company_code` and email global-uniqueness assumptions.** `auth_service.register` requires `company_code` unique and email globally unique across the whole `users` table (not per-company). A marketplace supplier's email living in a *different* table avoids a collision, but if a future ticket ever merges identity tables, this existing global-uniqueness constraint would need re-examining.
5. **No rollback complexity for the migrations above** (both are pure additions — new tables only), but the **frontend parallel-auth-stack pattern** (three independent `localStorage` keys) needs a manual QA pass confirming a browser can hold a tenant session, a platform session, and a supplier session simultaneously without cross-contamination, mirroring the check already informally done for tenant+platform on Day 28.

## 7. Rollback and feature-flag plan

- Each migration's `downgrade()` simply drops its new tables (no data in existing tables touched) — safe to roll back in isolation, same as migration 0022.
- Recommend gating new UI entry points (sidebar links, new portal routes) behind nothing-fancier-than-"don't link to it until it's real," the same discipline already used in `platform-shell.tsx` (only `Overview`/`Companies` are shown; the rest of Epic 27's sidebar items from the Octax spec are deliberately omitted because they're not built) — consistent with this project not having a feature-flag system and not needing one yet given its single-deployment, incremental-ticket model.
- No existing route, table, or column is renamed or removed anywhere in this plan — purely additive, so there is nothing to roll back on the existing surface even if a new module is abandoned mid-build.

## 8. Ticket-to-file implementation map

| Ticket | New files | Touches existing |
|---|---|---|
| BUILD-146 CRM leads/pipeline | `models/crm.py`, `services/crm_service.py`, `schemas/crm.py`, `api/v1/platform_crm.py`, migration `0023`, `frontend/.../platform-admin/crm/*` | `api/v1/router.py` (register router only) |
| BUILD-147 Supplier mgmt/verification | `models/marketplace_supplier.py`, `services/marketplace_supplier_service.py`, migration `0024` | `platform_company_service.py`-style new platform endpoints only |
| Supplier Portal auth (prerequisite for 147/148) | `services/marketplace_supplier_auth_service.py`, `api/v1/supplier_portal.py`, `frontend/.../supplier-portal/*`, parallel frontend auth stack | `core/security.py` (new token-type literals, same pattern as `platform_access`), `tests/test_api_authorization_http.py` (new public routes) |
| BUILD-148 Marketplace activity | depends on 147 existing first | — |
| BUILD-149 Subscriptions | new `models/subscription.py` + migration; no payment provider chosen yet (blocked, per tickets.md) | — |
| BUILD-150 Commissions | depends on 148 | — |
| BUILD-151 Platform payments/invoices | depends on 149 | — |

---

**Waiting for approval before writing any code.** No existing files were modified in this audit. The one open question worth a decision before implementation starts: should the Supplier Portal's own login (prerequisite for 147/148) be built now as part of CRM work, or deferred until a marketplace supplier model is actually needed — CRM leads/pipeline (BUILD-146) has no dependency on it and could start independently.
