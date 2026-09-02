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

The palette is **Soul Palette V2.1** (Reed, approved 2026-08-29), adopted VERBATIM and
merged 2026-09-01. Contract + spec: `docs/design/soul-palette-v2.1-origin.css` and
`docs/design/merged-palette-and-components.html`. The conversion app and the portal
share these token names and values — changing a V2.1 value is a cross-app decision.

- **Surfaces/ink:** `--background --card --muted --band --border --input --foreground
  --muted-foreground --primary --primary-foreground --ring`. Light is white-grounded;
  dark is the V2.1 navy (`#0B1723` page, `#14202D` card) — NOT the old near-black.
- **Status is a PAIR, and the pair flips with the theme by itself:** `ok/ok-bg`,
  `over/over-bg`, `warn/warn-bg` (Tailwind: `text-ok bg-ok-bg`, `text-over bg-over-bg`,
  `text-warn bg-warn-bg`). Never write emerald/red/amber classes again, and never add a
  `dark:` variant to a status token — the token already carries both columns.
- **Headings:** `--heading` is ink for page titles; `--heading-accent` is the V2.1 teal
  and belongs on the small uppercase eyebrow above them (`text-heading-accent`).
- **Ramps:** `--neutral-0..6`, `--brand-blue-1..3`, `--brand-teal-1..3`.
- Everything else (`--surface*`, `--chip*`, `--btn-ghost*`, `--tooltip*`, `--mesh-glow*`,
  `--foreground-muted`, `--accent`) is DERIVED from those in globals.css — change the
  base token, not the derivation.
- NO Tailwind palette classes in app components. `audit-brand.mjs` fails the build on
  any `text|bg|border|ring|from|via|to-{sky,emerald,red,amber,indigo,violet,cyan,rose,
  green,orange,purple,fuchsia,pink}-NNN`. Allowlisted: the login page (deliberately
  fixed-light with the navy panel) and the print-pack headers (fixed-light for paper).
- Print (council/lineage packs): the `@media print` block forces tokens to fixed light
  values inside `.council-pack` / `.lineage-pack` / `#dashboard-export-root`.

## Charts — one renderer, one colour rule

- `builder/BuilderChart` (+ `ui/chart.tsx` primitives) is THE chart renderer.
  `MiniSparkChart` is the only other (KPI sparklines). Never add a third; never
  reintroduce raw Recharts with hex colours (the deleted ChartView anti-pattern).
- **Categorical series come from `--chart-1..6`** — blue and teal only. Teal is NEVER
  paired with blue as a category; two-series charts use chart-1 with chart-3.
- **Value ramp rule (app-wide):** single-series bars are coloured by MAGNITUDE —
  `--primary` at the top of the range shifting to the palette's own `over` red at the
  bottom, so the suite has exactly one red. Interpolated in **Oklab**, not HSL: a hue
  sweep between those endpoints takes the short way round the wheel and renders
  mid-range values as vivid magenta/violet (the 2026-09-01 bug — bars that looked like
  a third category). `lib/chartEmphasis.ts` `valueRampColors(values, {dark})` — the
  anchors differ per theme, so callers pass `colorMode`. Unit-tested including the
  magenta guard; change the tests first.
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
  fences. Frontend `npm run test` (vitest); backend `pytest tests/ -q` from the
  repo root — pytest collects BOTH the unittest.TestCase modules and the
  pytest-style ones, so a bare `python -m unittest` silently errors on two files.
  Install with `pip install -r deploy/requirements-dev.txt`. Both suites gate CI
  (portal-ci, api-ci).
- **Propagate everywhere**: a change in one place updates its siblings (both brand
  sources, fence + its tests + templates + loader, etc.) in the same commit.
- **Lean pass before the commit.** Writing the code is not the last step: read it
  back as a reviewer and DELETE what doesn't earn its place — duplicated logic
  (factor it to one place), temporary scaffolding and dead branches, and comments
  that narrate the code or the change instead of stating a constraint. The bar is
  absolute: tests stay green and behaviour is unchanged. The tests written first
  are what make the deletion safe.
- Never run `next build` while `next dev` is live (corrupts `.next`).
- Verify against real data: local INT_DEV Postgres VPN-free; Ellensburg 25.4 Oracle
  (the authentic C2M validation target) when VPN is on.
- Reporting column names are a Jaspersoft contract — presentation changes only.

## Bug classes this codebase actually produces (QA sweep 2026-08→09)

Each found more than once. Hunt these by pattern; clicking around finds them slowly.

1. **The second list.** A hardcoded copy of catalog/registry data, drifting silently.
   Three instances: the admin grant picker, `businessLabels`
   WORKSTREAM_ORDER/LABELS/DESCRIPTIONS, `workstreamIcons`. Consequences were invisible
   — Asset Operations was ungrantable, and `/workstream/assets` 404'd while
   `/workstream/new_services` rendered a full dashboard. **THERE ARE TWO DEPLOYMENT
   SHAPES**, which is why these copies rot: `output/catalog_dbt.json` has `assets` and
   no `new_services`; `output/catalog_cisadm.json` has `new_services` and no `assets`
   (six orgs are legacy). No single hardcoded list can be right for every org. Derive
   per organization from `workstream_order`; where a shape-independent fallback is
   genuinely needed it must carry the UNION and be pinned by a test that reads
   `output/catalog_*.json` — both files are committed, so the test can.
2. **Shape mismatch across the API boundary, masked by a fallback that never runs.**
   `workstreams[].featured` is id STRINGS; the hero read `.snapshot_id`, so every
   "Start here" card on every workstream page rendered blank and linked to
   `/explore/undefined`. The object shape it expected came only from its own fallback
   branch, which never ran — so the code read as correct and no catalog data could have
   fixed it. Accept both shapes at the seam, and assert the rendered href, not merely
   that something rendered.
3. **The message describes a scope the query did not apply.** Scheduled emails, alert
   emails, the DQ headline, the "Data refreshed" pill, "Date filter: Reporting period".
   Wherever copy names a window or filter, check the query actually carried it.
4. **A migration silently dropped a semantic.** Soul Palette V2.1 rewrote
   `from-sky-500/10` to `from-primary`; Tailwind cannot apply an opacity modifier to a
   raw `var()`, so the alpha vanished and nine tint surfaces became opaque blocks over
   their own unchanged text (1.00:1 — invisible). Grep a migration diff for what the
   NEW form cannot express.
5. **A token validated on one surface, used on another.** Dark `--foreground-subtle`
   was 5.36:1 on the page ground and 4.20:1 on `--muted`, where it also lives. Check a
   colour role against the lightest/darkest surface it actually lands on.
6. **A control that widens, worded as if it narrows.** Deleting an access group gives
   its members FULL access (`workstreams_allowed` treats empty as all). Say the real
   consequence in the confirm.
7. **The UI implies an authorization boundary the backend does not implement.** See
   originba-security on admin scope. If a field looks like it scopes someone, confirm a
   query actually filters on it.

**Your own QA tooling lies too — verify before reporting.** All of these produced
convincing false positives here: `backgroundColor` cannot see a gradient, so
white-on-gradient reads as white-on-white (ratio exactly 1.00); treating the
translucent mesh page-glow as opaque flags text nowhere near a glow — evaluate the
radial gradients at the element's own position; recharts leaves `fill="#ccc"` as an
ATTRIBUTE while CSS overrides it, so read `getComputedStyle`; `read_console_messages`
replays a stale buffer including mid-edit HMR errors and pre-restart CORS failures;
`npx tsc --noEmit | tail -5 && echo clean` prints "clean" unconditionally because the
exit code is `tail`'s. A ratio of exactly 1.00, or a suspiciously uniform cluster, is
the tool and not the app until proven otherwise.

## Enterprise features (shipped 2026-09-01, all tests-first)

- **SSO/OIDC** (`api/auth/oidc.py` + `/auth/oidc/*`): Azure AD auth-code flow, signed
  HS256 state, RS256 id_token via JWKS. JIT-provisions role `user` in
  OIDC_DEFAULT_ORGANIZATION — SSO NEVER mints admins. SPA gets our JWT via the login
  page's `#sso_token=` fragment (fragments stay out of server logs). Routes call
  helpers through the `oidc.` namespace so tests can patch them.
- **Scheduled delivery + KPI alerts** ride ONE hourly cron: `python -m
  api.report_schedule_runner` (`--dry-run` renders only). Schedules mail a saved view
  as CSV (business labels, True/False); alerts watch exec KPIs via the SAME
  execute_kpi_definition the dashboard uses and notify ONLY on the transition into
  breach. Both org-scoped in portal_state (local JSON fallback), both capped, SMTP_*
  env. UI: ScheduleDialog (saved views), KpiAlertsDialog (exec toolbar).
- **Access audit** (`api/access_audit.py`): report runs, SQL executes AND fence
  refusals land in portal_audit_log; the writer swallows failures by design — an
  audit outage must never 500 a query. `/auth/audit-log?action=` filters.
- **Annotations** (`api/annotations.py`, NotesDialog): notes on saved_view/dashboard/
  dashboard_tile; author-or-admin delete.
- **Backup**: `deploy/backup_portal_state.sh` (auth tables + portal_state schema).
- **Dialogs**: `components/Modal.tsx` is THE shell (overlay, click-outside AND
  Escape to close, `role="dialog"`, header + close button), with `SmtpNotice` and
  `FormError` beside it. Schedule/Alerts/Notes all use it; never hand-roll a fourth
  modal, and use the app's `.btn-primary` rather than a new button style.
- **Guardrails live in libs, tested**: `visualGuardrails` (pie >30 slices, 1-series
  stacked → disabled with reason), `dashboardTileMath` (tile charts the FIRST
  measure's column; KPI headline sums only sum/count), `databaseChartUtils`
  (identifier columns never chart as measures), `axisLabels.tickLabels` (truncate
  ONCE; head…tail when two labels would collide), `recipients.parseRecipients`.
- **Errors**: `fetchJson` runs `parseApiError` once, so `err.message` is already a
  human message everywhere — never re-parse JSON at a call site.
- **Pinning**: PinMenu targets a NEW or EXISTING dashboard; pins APPEND to the first
  free slot, never replace.
- **A11y baseline**: global `:focus-visible` ring, `role="img"` + descriptive
  aria-label on every chart, click/Enter adds fields (drag is optional).
- Route-test hygiene: modules share one interpreter — pin `PORTAL_AUTH_DISABLED` etc.
  per test class with `mock.patch.dict(os.environ, ...)`, never rely on import-time env.
