# BuildOS AI — Ticket Backlog

Full backlog from the product plan, grouped by epic. Status legend: `[ ]` todo, `[~]` in progress, `[x]` done.

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
- [ ] BUILD-010 AI executive summary

## Epic 3 — Projects
- [x] BUILD-011 Project CRUD
- [x] BUILD-012 Project dashboard
- [x] BUILD-013 Project members
- [x] BUILD-014 Project milestones
- [x] BUILD-015 Project tasks

## Epic 4 — BOQ
- [x] BUILD-016 BOQ management
- [x] BUILD-017 BOQ calculations
- [ ] BUILD-018 BOQ vs Actual
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
- [ ] BUILD-037 Supplier transaction history (blocked on Purchase Orders — Epic 8)
- [ ] BUILD-038 Supplier performance (blocked on Purchase Orders — Epic 8)
- [ ] BUILD-039 AI supplier insights (blocked on Purchase Orders — Epic 8)

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
- [ ] BUILD-059 Daily report
- [ ] BUILD-060 Daily report list
- [ ] BUILD-061 Photo uploads
- [ ] BUILD-062 AI daily report generation

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
- [ ] BUILD-072 Document upload
- [ ] BUILD-073 Document categories
- [ ] BUILD-074 Document preview/download
- [ ] BUILD-075 Document metadata

## Epic 15 — AI Document Intelligence
- [ ] BUILD-076 Document text extraction
- [ ] BUILD-077 Document chunking
- [ ] BUILD-078 Embeddings
- [ ] BUILD-079 Vector storage
- [ ] BUILD-080 RAG search
- [ ] BUILD-081 Document Q&A

## Epic 16 — AI Copilot
- [ ] BUILD-082 AI chat interface
- [ ] BUILD-083 Conversation history
- [ ] BUILD-084 Project-aware AI context
- [ ] BUILD-085 Database tool calling
- [ ] BUILD-086 Natural language analytics
- [ ] BUILD-087 AI recommendation engine

## Epic 17 — Project Risk
- [ ] BUILD-088 Risk model
- [ ] BUILD-089 Project health score
- [ ] BUILD-090 Risk dashboard
- [ ] BUILD-091 AI risk explanation

## Epic 18 — Scheduling
- [ ] BUILD-092 Project schedule
- [ ] BUILD-093 Tasks with dependencies
- [ ] BUILD-094 Milestones
- [ ] BUILD-095 Progress tracking
- [ ] BUILD-096 Basic Gantt
- [ ] BUILD-097 Schedule variance
- [ ] BUILD-098 AI delay analysis

## Epic 19 — Notifications
- [ ] BUILD-099 Notification system
- [ ] BUILD-100 Notification center

## Epic 20 — Search
- [ ] BUILD-101 Global search
- [ ] BUILD-102 AI semantic search

## Epic 21 — Settings
- [ ] BUILD-103 Company settings
- [ ] BUILD-104 User settings
- [ ] BUILD-105 Role permissions
- [ ] BUILD-106 Currency/unit settings
- [ ] BUILD-107 AI settings

## Epic 22 — Reports
- [ ] BUILD-108 Project report
- [ ] BUILD-109 Inventory report
- [ ] BUILD-110 Procurement report
- [ ] BUILD-111 Expense report
- [ ] BUILD-112 AI executive report

## Epic 23 — UX Polish
- [ ] BUILD-113 Responsive layout
- [ ] BUILD-114 Loading states
- [ ] BUILD-115 Skeleton loaders
- [ ] BUILD-116 Empty states
- [ ] BUILD-117 Error states
- [ ] BUILD-118 Toast notifications
- [ ] BUILD-119 Confirmation dialogs
- [ ] BUILD-120 Form validation

## Epic 24 — Security
- [ ] BUILD-121 API authorization
- [ ] BUILD-122 Tenant isolation
- [ ] BUILD-123 Input validation
- [ ] BUILD-124 File upload validation
- [ ] BUILD-125 Rate limiting
- [ ] BUILD-126 Audit log

## Epic 25 — Testing
- [ ] BUILD-127 Backend unit tests
- [ ] BUILD-128 API integration tests
- [ ] BUILD-129 Authentication tests
- [ ] BUILD-130 Inventory tests
- [ ] BUILD-131 Procurement tests
- [ ] BUILD-132 Project tests
- [ ] BUILD-133 AI tests
- [ ] BUILD-134 Frontend critical-flow tests

## Epic 26 — Deployment
- [ ] BUILD-135 Production Docker setup
- [ ] BUILD-136 Production database
- [ ] BUILD-137 Environment configuration
- [ ] BUILD-138 Storage configuration
- [ ] BUILD-139 Domain/SSL
- [ ] BUILD-140 CI/CD
- [ ] BUILD-141 Database backup
- [ ] BUILD-142 Logging/monitoring
