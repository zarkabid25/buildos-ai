# BuildOS AI 2.0 — Global UI/UX Design Instructions

These instructions are mandatory for every development phase and every new frontend component, across all four BuildOS AI interfaces:

1. Platform Super Admin
2. Construction Company Portal (the existing ERP)
3. Supplier Portal
4. Public Marketing Website

All four must look like products from the same company, while each keeps its own layout and information hierarchy.

## CRITICAL — Preserve Existing ERP

The current Construction Company ERP is already developed. DO NOT:
- Replace its layout, redesign its dashboard, or change its existing colors without approval.
- Replace working UI components or change existing navigation unnecessarily.
- Break responsive behavior or modify existing business workflows for visual reasons.

Before building new pages, inspect the current design system and reuse existing components and tokens wherever possible. New marketplace/subscription pages must look native to the existing ERP.

## Portal 1 — Platform Super Admin

References: Linear, Attio CRM, Stripe Dashboard.

Visual direction: premium enterprise SaaS, dark charcoal/navy sidebar, light-gray page background, white cards/tables, thin borders, compact but readable layouts, clean typography, minimal shadows, professional charts, restrained micro-interactions.

Layout: fixed/collapsible left sidebar; topbar with global search, notifications, user menu; breadcrumbs and page titles; clear primary action buttons; responsive content area.

Required screens: business dashboard, CRM leads/pipeline, company management, supplier management, supplier verification, marketplace activity, subscription management, commission tracking, payments/invoices, support tickets, AI business intelligence.

Dashboard metrics: active companies, active suppliers, MRR, new leads, pending supplier verifications, marketplace order volume, earned commissions, outstanding payments, recent activity, revenue/conversion charts.

CRM: Kanban pipeline, advanced filterable tables, contact profiles, activity timeline, follow-up reminders, deal detail drawer.

Should feel like a sophisticated business management application, not a generic admin template.

## Portal 2 — Construction Company Portal

References: existing BuildOS AI ERP (visual source of truth), Linear-style interaction patterns, construction-focused workflow organization.

New pages: supplier marketplace, supplier search, supplier detail, supplier connections, marketplace RFQs, quotation comparison, subscription/billing, marketplace order tracking.

New pages must reuse the existing sidebar, topbar, typography, colors, table/card patterns, form controls, dialogs and notifications. Do not create a second company dashboard when the existing one already works.

Supplier discovery needs: search, category filters, location filters, supplier cards, verification indicators, delivery coverage, product catalog, request-quotation action. Quotation comparison must prioritize clear, readable data for purchasing decisions.

## Portal 3 — Supplier Portal

References: Shopify Admin, modern B2B vendor management apps.

Visual direction: clean white/light-gray workspace, simple navigation, blue primary actions, restrained teal accents, minimal cognitive load, mobile-first forms/workflows.

Required screens: supplier dashboard, company profile, product catalog, RFQ inbox, submit quotation, quotation history, orders, delivery updates, commission statements, support.

Priorities: fast quotation entry, simple product editing, clear order statuses, easy document uploads, large touch targets on mobile, straightforward navigation. A supplier must be able to open an RFQ, enter prices, and submit a quotation without unnecessary steps.

## Portal 4 — Public Website

References: Linear marketing site, Vercel marketing presentation, premium B2B SaaS landing pages.

Visual direction: strong typography, spacious layout, premium construction photography, clean product screenshots, dark navy and white sections, blue accent, subtle animations, modern pricing cards, professional footer.

Pages: Home, Features, Construction ERP, Supplier Marketplace, Pricing, About, Contact, Request Demo, Company Signup, Supplier Application.

Homepage sections: hero with strong positioning; ERP + marketplace value prop; product screenshots; how it works; benefits for construction companies; benefits for suppliers; AI features; pricing; FAQ; final CTA.

Do not use fake customer logos, testimonials, statistics, or endorsements.

## Shared Design Tokens

Suggested defaults for NEW portal surfaces (use the existing ERP's actual tokens wherever a new screen is integrated into the ERP):

| Token | Value |
|---|---|
| Primary | #2563EB |
| Sidebar | #111827 |
| Background | #F8FAFC |
| Surface | #FFFFFF |
| Accent | #0D9488 |
| Heading | #0F172A |
| Muted Text | #64748B |
| Border | #E2E8F0 |
| Success | #16A34A |
| Warning | #D97706 |
| Danger | #DC2626 |

(Existing ERP tokens per `CLAUDE.md`: Background #F7F8FA, Surface #FFFFFF, Sidebar #111827, Primary #2563EB, Success #16A34A, Warning #F59E0B, Danger #DC2626, Text #111827, Muted #6B7280, Border #E5E7EB — reuse these on existing ERP screens; the table above is for genuinely new portals only.)

## Frontend Stack

Reuse the existing Next.js 14, React, TypeScript, Tailwind CSS, shadcn/ui, Lucide icons, and existing API hooks/chart/table dependencies. Do not add a new UI framework without approval.

## Mandatory UX Requirements (every page)

Clear page title and description; appropriate primary action; loading and skeleton states; useful empty states; actionable error messages; success/error toast notifications; form validation; responsive layout; keyboard accessibility; confirmation dialogs for destructive actions; consistent status labels; appropriate pagination/filters for large datasets. Use reusable components rather than duplicating styles across pages.

## Visual Quality Rules — Avoid

Generic admin-template appearance; excessive gradients; oversized colorful cards; random colors; inconsistent spacing; unnecessary animations; emoji as primary navigation icons; dense forms without grouping; tables without filters or pagination; unreadable small text; placeholder functionality disguised as working features.

## Required Design Workflow (per new portal/major module)

1. Inspect the existing design components.
2. Define the page hierarchy.
3. Describe the intended layout and user flow.
4. Identify reusable components.
5. Implement the real API-backed frontend.
6. Check desktop, tablet and mobile layouts.
7. Verify loading, empty, error and success states.
8. Check keyboard and screen-reader accessibility.
9. Capture screenshots if browser tooling is available.
10. Review visual consistency with the portal reference.
11. Run frontend tests and build checks.

## Final Requirement

The four interfaces must look like products from the same company. Platform Admin: premium and data-focused. Construction Company Portal: preserves the current ERP experience. Supplier Portal: simple and efficient. Public Website: polished and commercially credible.

Never sacrifice existing functionality or security to achieve a visual redesign.
