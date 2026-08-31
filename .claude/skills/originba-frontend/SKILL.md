---
name: originba-frontend
description: The OriginBA portal front-end conventions — Origin brand, theme tokens, one chart renderer, the value-ramp colour rule, flat axes, TDD. Load before any UI work in apps/analytics-portal.
---

# OriginBA front-end conventions

The portal (apps/analytics-portal: Next.js 15, React 19, Tailwind 3, recharts, @dnd-kit)
is an opinionated BI tool: ONE obvious way to do each thing. These rules were each earned
during the 2026-08 overhaul; breaking one usually reintroduces a bug we already fixed.

## Brand (Origin)

- Assets: `public/origin-logo.png` (full colour, light surfaces), `origin-logo-white.png`
  (dark surfaces), `origin-mark.png` (the infinity mark alone). Rasterised from the
  vendor vector — replace with an SVG export for infinite crispness, never redraw it.
- `BrandMark` renders the logo theme-aware; `mark` prop for compact spots.
- Brand values live in TWO places that must agree: `src/lib/brand.ts` (DEFAULT_BRAND)
  and `config/analytics_portal_client.json` (the runtime source the API serves).
- Colours: `--brand` (#2f74b8 light / #5b9bd8 dark), `--brand-navy` (#16283c).
- The LOGIN PAGE is deliberately light regardless of app theme (reference design):
  `.login-input` fixed-light class, navy brand panel right, logo pinned top-left.

## Theme tokens — never hardcode a colour

- All colour comes from tokens in `globals.css` (`:root` light, `.dark` overrides),
  registered as Tailwind classes: `text-fg`, `text-fg-muted`, `text-fg-subtle`,
  `text-heading`, `bg-surface(-subtle/-solid/-input)`, `border-edge(-subtle)`,
  `bg-chip`, `text-brand`, `chart.1-5`, `chart-selected`.
- NO `text-white` / `text-slate-*` / `bg-white/10` in app components — the compat shim
  that used to remap them is DELETED; a hardcoded class now renders literally. The only
  legitimate `text-white` sits on intentionally fixed backgrounds (brand logo tile,
  login navy panel).
- Dark mode is near-black by design (#0b0d12 ground, #14171f cards) per the reference
  dashboard. Every change is verified in BOTH themes before commit.
- Print (council/lineage packs): the `@media print` block forces tokens to fixed light
  values inside `.council-pack` / `.lineage-pack` / `#dashboard-export-root`. Token
  classes print correctly; do not add print-only hardcoded colours.

## Charts — one renderer, one colour rule

- `builder/BuilderChart` (+ `ui/chart.tsx` primitives) is THE chart renderer.
  `MiniSparkChart` is the only other (KPI sparklines). Never add a third; never
  reintroduce raw Recharts with hex colours (the deleted ChartView anti-pattern).
- **Value ramp rule (app-wide):** single-series bars are coloured by value —
  BLUE (hue 207) = highest, shifting toward RED (368≡8) as values drop, interpolated
  the WARM way round the wheel so the ramp never passes green (green falsely reads
  "good"). Implementation: `lib/chartEmphasis.ts` `valueRampColors` — unit-tested;
  change the tests first.
- Cross-filter selection overrides a bar/slice to `var(--chart-selected)` (amber).
- **Axis text is FLAT — never rotated.** Long labels truncate (`slice + …`) with
  `interval="preserveStartEnd"` / `minTickGap`; grids/axes colour from
  `--border-subtle` / `--foreground-subtle` only.
- Booleans render as True/False everywhere (`formatBoolean` / `formatCellValue`
  `isBoolean`), driven by the column's declared type — never raw 1/0.
- Panel headers lead with a small rounded icon chip coloured from the chart palette
  (see DashboardWidget) — the reference-dashboard signature.

## Information architecture — one job per surface

Home (exec KPIs) · Explore `/build` (THE builder; deep links `?canvas=&report=`) ·
Dashboards `/dashboards` (@dnd-kit pinboard) · Library `/reports` (catalog + workstream
rail) · SQL `/database` (CISADM workspace; `?table=` seeds a query) · Data Quality ·
Settings. `/explore/[snapshotId]` is the canvas overview (Reports + Data model only —
builder/SQL tabs redirect out). Never add a second builder/SQL/chart surface.

## SQL workspace rules

- Users query CISADM (the schema they know), never our reporting/staging internals.
  The fence (`api/sql_workspace_validator.py`) allows cisadm + reporting only, and
  BLOCKS secrets: MICR_ID, WEB_PASSWD*, ALERT_INFO, and SELECT * on CI_PAY_TNDR.
- Log tables (\*_LOG, \*_LOG_PARM, \*LOGPARM) are excluded from the table browser —
  no business value. Table guide lines live in `lib/cisadmTableGuide.ts`.
- Starter queries speak CISADM (freeze_sw='Y', bill_stat_flg='C', ci_cust_cl_l ENG
  labels), dialect-aware per engine.

## Working discipline

- **Tests first** (red → green) for any pure logic: formatters, ramps, swap logic,
  fences. Vitest (`npm run test`) frontend, unittest backend.
- **Propagate everywhere**: a change in one place updates its siblings (both brand
  sources, fence + its tests + templates + loader, etc.) in the same commit.
- Never run `next build` while `next dev` is live (corrupts `.next`).
- Verify against real data: local INT_DEV Postgres VPN-free; Ellensburg 25.4 Oracle
  (the authentic C2M validation target) when VPN is on.
- Reporting column names are a Jaspersoft contract — presentation changes only.
