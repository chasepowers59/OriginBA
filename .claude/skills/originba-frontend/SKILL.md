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
8. **A store-level test cannot see what the request schema already dropped.** The saved
   view store had handled `measures` for months, with a comment; `SavedViewCreate` never
   declared the field, and Pydantic discards what it does not declare, so every
   multi-measure view reopened with one measure. `filters` was missing end to end, so a
   scoped view reopened over the whole canvas ($21,355.94 wrong on the probe). The
   existing test called `create_saved_view()` DIRECTLY and passed throughout. Round-trip
   persistence through the ROUTE (`tests/test_saved_view_route_fidelity.py`), and when
   you add a field to a store, grep for the Pydantic model in front of it.
9. **A control that shows a different scope than it applies.** The filter value picker
   caps distinct values at 100 and a `<select>` whose value matches no option silently
   shows its first — "choose value…" over a live `WHERE` returning 0 rows. Any picker
   backed by a capped list must admit its current value.

10. **A fixed-width child that never yields.** Both responsive failures found were this:
    `/database`'s 288px `w-72 shrink-0` sidebar left ~55px for the editor at 375px (the
    placeholder wrapped to one character per line, "Results" clipped to "Resu"), and
    `/explore`'s grid item defaulted to `min-width:auto` so one wide child sized the
    column to 860px and scrolled the whole PAGE sideways. Fixes: stack below a
    breakpoint, and `min-w-0` on every flex/grid child that holds wide content — the
    codebase already uses `flex min-w-0 flex-1` for exactly this.
    Related: `flex-1` on a `flex-wrap` row is `flex-basis: 0`, so the child collapses
    beside its siblings instead of wrapping — use `basis-full sm:basis-0 sm:flex-1`.
    **Test it by measuring, not looking**: `document.body.scrollWidth > clientWidth`
    catches the page-level failure, and an element wider than the viewport is only OK
    if an ancestor's `overflow-x` is auto/scroll AND `scrollWidth > clientWidth` — the
    DQ tables pass that (946px reachable inside 293px), a clipped panel does not.
    Layout-dependent copy is part of this: "from the left panel" was wrong once the
    panel stacked above.

**The catalog's `default_date_field` can be a measured-empty column.** It is
`dates[0]` — the canvas's FIRST date column in field order — and the generator has no
database access, so it cannot know the column is empty. Measured at Ellensburg
2026-09-02:

| canvas               | default_date_field    | rows with a value      |
| -------------------- | --------------------- | ---------------------- |
| RPT_CUSTOMER_ACCOUNT | Bill After Date       | 7 of 92,824 (0.008%)   |
| RPT_DEVICE_ASSET     | Retirement Date/Time  | 184 of 55,082 (0.3%)   |
| RPT_BILL             | Window Start Date     | 364,382 of 724,762 (50%) — while Bill Date is 99.4% |

Most defaults ARE fine (RPT_PREMISE_SP, RPT_PAY_PLAN, RPT_SERVICE_AGREEMENT,
RPT_CREDIT_RATING_HISTORY all 100%), so this is a per-canvas defect, not systemic. But a
user who drags the offered default onto Filters gets a near-empty chart with nothing
explaining why — and `build_portal_catalog`'s own comment already describes this exact
failure for the SIBLING field: "Auto-picking its first date column and forcing a window
on it silently emptied results". `required_date_field` was fixed by setting it to None;
`default_date_field` kept the naive pick.

**It is load-bearing in five places, not just the builder's filter shelf.**
`report_schedules` windows a scheduled EMAIL on it, `tileDateField` gives a dashboard
tile its time axis, `kpi_runner` and `nlq_metrics` window their metrics, and
`dateScope` sets the builder's scope. Measured consequence on demo25, a 90-day window:

    rpt_device_asset      old field 0 rows      new field 93 of 1,282
    rpt_field_activity    old field 0 rows      new field 54 of   330

Zero. Four NLQ metrics (new_service_agreements, never_registered_devices,
meterless_service_points, open_todos) declare no date_field of their own and are not
windowless, so they returned 0 unconditionally whatever the data said. The executive
KPIs escaped only because they carry explicit overrides — `total_customers` is
`windowless: True`, `bills_completed` and `field_activities` name "Created Date/Time".
Those overrides were needed BECAUSE the default was wrong: per-KPI patches for a
catalog-level defect.

Fixing it needs population data the catalog generator does not have. The clean route:
`build_data_dictionary` already reads the built warehouse and already chooses each
canvas's date column for the index — have it choose by measured population and write
that into `_reporting.yml`, which the catalog then reads. That keeps the index column
and the UI default the same column by construction, which is the property the index
derivation already depends on. PRODUCT-VISIBLE (it changes which date the UI offers
first, and which column gets indexed), so decide before doing.

**The business-process layer is dark on dbt orgs.** `build_portal_catalog` emits
`"business_processes": []` hardcoded, with no comment — and every other deliberate
emptiness in that file carries one, which is the tell for a placeholder rather than a
decision. Measured from the committed catalogs:

    catalog_cisadm   21 business_processes, 19 of 19 canvases with process_guides
    catalog_dbt       0 business_processes,  0 of 38 canvases with process_guides

The UI is wired for it end to end, so it fails quietly on the three dbt orgs —
including Ellensburg, the strategic target. Two consequences:
`ExplorerPanel`'s process-guide panel never renders (benign omission), and
`WorkstreamExplorer`'s search box — placeholder "Search processes…" — can only ever
match workstream NAMES, because `.filter(ws => ws.processes?.length > 0 || label
matches)` has nothing to search. Empty query shows everything; typing anything
collapses it to label hits.

Porting it is CONTENT work (process definitions and field guides for 38 canvases), not
just code, so it is a product decision rather than a fix to slip in.

**Dead-code sweeps need three guards, learned the hard way.** (1) `grep --include=*.ts`
inside zsh globs the pattern before grep sees it and reports EVERY module as unimported.
(2) An import-graph scan that ignores `await import("./x")` calls live code dead — that
nearly took `saveFavorite`/`removeFavorite`. (3) A Python scan over `api/` reported 54
dead functions, almost all FastAPI route handlers referenced by their DECORATOR, not by
name; a detector that does not skip decorated defs would delete the API. After all
three filters: 0 unused modules, 10 dead frontend exports (162 lines), 9 undecorated
backend candidates.

**An unused function that documents its purpose is a question about the CALLER.**
`warehouse_db.connection_info` said "Masked, for the settings page" and the settings
page never called it — because `public_status` only checked the Oracle paths, so a dbt
org read "Not configured" while `/snapshots` said `db_configured: True` and queries
returned rows. Same for `filter_kpis_for_auth`: an unused SECURITY filter beside four
used siblings turned out to mark a rule that half the family re-implemented and
disagreed on. Follow these before cutting them.

**Shared rules beat mirrored ones.** buildRequest and saveView each decided which
filters were "live"; only one of them existed, so the saved view was not the view that
ran. When two code paths must agree about the same thing, give them one function
(`lib/builderFilters.activeFilters`) rather than two implementations to keep in step —
the same reasoning as deriving workstreams from the catalog instead of copying them.

**Your own QA tooling lies too — verify before reporting.** All of these produced
convincing false positives here: `backgroundColor` cannot see a gradient, so
white-on-gradient reads as white-on-white (ratio exactly 1.00); treating the
translucent mesh page-glow as opaque flags text nowhere near a glow — evaluate the
radial gradients at the element's own position; recharts leaves `fill="#ccc"` as an
ATTRIBUTE while CSS overrides it, so read `getComputedStyle`; `read_console_messages`
replays a stale buffer including mid-edit HMR errors and pre-restart CORS failures;
`npx tsc --noEmit | tail -5 && echo clean` prints "clean" unconditionally because the
exit code is `tail`'s; and auditing in the SAME call that toggles the theme measures a
half-applied state (50 "failures" including nav links that pass — set the mode, reload,
then measure). A ratio of exactly 1.00, or a suspiciously uniform cluster, is the tool
and not the app until proven otherwise.

**A colour emoji ignores `color` entirely**, so it can MASK a contrast failure in the
element it sits in: replacing 📅 with a text glyph in the field palette immediately
exposed a 2.86:1 badge that had been failing all along. When a design mixes emoji and
text glyphs, audit the text ones separately.

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
