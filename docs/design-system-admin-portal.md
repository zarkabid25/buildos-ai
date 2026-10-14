# BuildOS AI Admin Portal — Design System

Applies to `/platform-admin/*` only (the Platform Super Admin portal). The existing
Construction Company ERP, its routes, tokens and components are unaffected — this
spec is additive and scoped under the `.buildos-admin` CSS class, never global
selectors. See `docs/design-system.md` for the broader four-portal spec this portal
belongs to; this file is the more detailed, authoritative one for this portal
specifically where the two differ.

## Reference

Visual language: **Octax — CRM Sales Dashboard & Analytics** (Iqbal Tahir / Portal
Studios), https://dribbble.com/shots/27618130-Octax-CRM-Sales-Dashboard-Analytics.
Reconstructed from the published images, not the designer's source file — treat
all numeric tokens as implementation estimates, not pixel-exact extraction.

Reproduce: white sidebar with a soft-gray selected row and a blue icon (not a
blue-filled block), a pale near-white canvas, white KPI cards with a pale-lavender
inset upper panel and a white footer, and understated bordered chart cards.
Do not reproduce the Octax logo, browser chrome, or any of its example data.

## Tokens

Defined as CSS custom properties scoped to `.buildos-admin` (see `globals.css`):
`--bo-canvas` #F8F9FB, `--bo-surface` #FFFFFF, `--bo-nav-active` #F3F3F4,
`--bo-kpi-surface` #F1F2FF, `--bo-border` #E6E7EB, `--bo-text` #17191D,
`--bo-text-secondary` #686B73, `--bo-text-muted` #777B85, `--bo-primary` #3D50FF,
`--bo-primary-soft` #EEF0FF, `--bo-success`/`--bo-success-bg`,
`--bo-danger`/`--bo-danger-bg`, `--bo-focus` #3045DD. Used via Tailwind arbitrary
values, e.g. `bg-[var(--bo-surface)]`.

## Components

- `MetricCard` (`components/platform/metric-card.tsx`): white outer card, 14px
  radius, lavender inset panel (label + icon, optional trend), large tabular-nums
  value, white footer with a date range and an optional "View details" link.
  Never fabricates a trend/comparison it doesn't have data for — shows an em dash
  instead.
- `UnavailableChartCard`: the honest-missing-data state for charts this portal
  can't render yet (no subscriptions/CRM/marketplace data exists). Matches the
  chart card's visual shell (border, radius, heading row) so the dashboard doesn't
  look broken, but is explicit that the data isn't there rather than faking a chart.
- `PlatformShell` (`components/platform-shell.tsx`): white 256px sidebar, bordered
  search input (visual only until a platform-level search endpoint exists — never
  wired to fake results), nav groups, soft-gray active row with a blue icon via
  `aria-current="page"`. White 64px topbar with a breadcrumb chip and account menu.

## What's intentionally not implemented yet

The reference's full IA (Leads, Deals & Pipeline, Suppliers, RFQs, Commissions,
Revenue Reports, Subscription Analytics) and its charts (Platform Revenue,
Acquisition Sources, Conversion) all need backend that doesn't exist yet — see
Epic 27 in `docs/tickets.md`. The sidebar and dashboard only show what's real
(Overview, Companies) rather than dead links or fabricated charts, per this
spec's own instruction not to fabricate functionality or hardcode metrics.
