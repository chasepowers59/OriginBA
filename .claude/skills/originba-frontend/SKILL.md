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
   a workstream the catalog did not carry rendered a full dashboard. The root cause was
   TWO catalog shapes coexisting — **retired 2026-09-02**: every org now reads
   `output/catalog_dbt.json`, and the legacy CISADM snapshot catalog is deleted. The
   lesson outlives the cause: derive from `workstream_order`, and pin any fallback
   against the committed catalog file with a test, because a hand-kept copy is the
   thing that drifts.
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

11. **ONE read of a shape-specific field, causing OPPOSITE bugs in the two shapes.**
    **CLOSED 2026-09-02 by retiring the second shape** — six instances of this class in
    one session was the case for it. Kept as the record of what the split cost and why
    a dormant branch is where the next one would have hidden. The shape-specific
    HEURISTIC variant (a rule that inspects a column NAME) still applies, because the
    SQL workspace passes raw CISADM column names while canvases are Title Case.
    The sharpest form of #1, and the hardest to see, because neither half looks like a
    bug on its own. `snapshot_explorer` chose its default window from
    `required_date_field` ALONE — a CISADM-era field no dbt canvas declares. Measured
    2026-09-02: 19/19 legacy canvases silently applied `BETWEEN today-90 AND today`
    (asked for all time, got a quarter, and only the returned raw SQL said so), while
    0/38 dbt canvases applied any window at all (unfiltered aggregate reads every row;
    the row cap cannot stop it because FETCH FIRST applies AFTER GROUP BY). Reading one
    file you would conclude the window works; reading the other, that it does not exist.
    **The fallback had already been written three times** — `kpi_runner`,
    `nlq_metrics` and `report_schedules` each fall back to `default_date_field`, and
    `report_schedules`' docstring describes this exact bug — and was never carried to
    the explorer. When a rule reaches a third caller, move it (`reporting_dates.
    window_date_field`) instead of fixing the fourth copy later.
    **A default the server chooses must be RETURNED, not merely applied.** Widening a
    silent window to 38 more canvases would have spread the legacy bug rather than fix
    it. The response now carries `applied_window` and one shared `AppliedWindowNote`
    renders it; a window the CALLER chose is never claimed as ours. The empty state was
    the strongest case: it said "Nothing matched your current filters" in exactly the
    situation where the reader had set none — sending them to hunt a filter that was
    not on screen. That is bug class #3 pointing the other way, and it is worth checking
    for directly: **copy that blames the reader's input for something the server did.**
    **The same root also produces shape-specific HEURISTICS, not just field reads**, and
    they are quieter because nothing errors. `measureIsCurrency` tested
    `includes("AMT")` — written for CISADM's `_AMT` suffix, and **"AMOUNT" does not
    contain "AMT"** — so of 47 money-ish measures in catalog_dbt exactly ONE was
    detected and canvas money rendered without a dollar sign. `prettifyFieldName` was
    the mirror image, written for the legacy form and mangling the canvas one. When you
    find a rule that inspects a column NAME, run it over every field id in BOTH
    `output/catalog_*.json` and read the diff; the count alone will not tell you.
    Prefer whole-TOKEN matching (split on non-alphanumerics — `\b` fails on `BILL_AMT`
    because underscore is a word character) over substrings, which err in both
    directions: widening the substring list newly matched "Days Unbalanced"
    (UNBALANCED contains BALANCE), "% of Arrears Collected" and a `_COUNT`. A specific
    negative set beats a lazy one — "Arrears 0-30 Days" IS currency, so excluding on
    "Days" would repeat the mistake.

12. **A calendar date derived in UTC.** Found on BOTH sides of the wire, weeks apart,
    which is what makes it a class rather than an incident. Backend:
    `report_schedules` ended its window on `datetime.now(timezone.utc).date()` while
    the other three builders used `date.today()`. Frontend: all three
    `defaultDateRange*` helpers ended `toISOString().slice(0, 10)` — `new Date()` is
    local but `toISOString()` converts. Measured under TZ=America/Denver: the end date
    read 2026-09-03 on 2026-09-02, and **"Prior month" ended 2026-09-01**, including a
    day of the one month it exists to exclude.
    These strings filter BUSINESS dates (Bill Date, Accounting Date) — calendar dates
    in the utility's own timezone, never UTC instants — so local is not merely
    consistent, it is the correct basis. **Invisible on a UTC machine**, which is how
    both survived; test with `TZ=America/Denver`, and for the constructed-midnight half
    (`new Date(y, 0, 1)` converts BACK a day east of UTC, so YTD starts in the prior
    year) with `TZ=Australia/Sydney`. `process.env.TZ` does take effect mid-process in
    this Node, so such a test is real rather than vacuous — verify that before trusting
    one. One home each: `api/reporting_dates.py`, `format.ts`'s `localIsoDate`.

13. **A missing value silently coerced into a real one.** `Number(null)` and
    `Number("")` are both `0`, so any formatter opening with `Number(value)` and
    rejecting only non-finite results turns NULL into a business fact. `formatCurrency`
    rendered a null amount as **"$0"** on the finance KPIs — while `undefined` rendered
    "—", and that inconsistency is the tell that neither was considered. Reachable by
    construction: SQL NULL serializes to JSON null and a SUM over zero matching rows IS
    null. The backend distinguishes the state deliberately
    (`kpi_runner.empty_window_note` branches on `value not in (None, 0)` to separate
    "none happened" from "none in the window you chose"), so the formatter erased the
    distinction that code exists to preserve. Guard `value == null || value === ""`
    BEFORE coercing — `formatCellValue` always did, which is how you can tell the
    convention existed and the others just missed it. Check the **tooltip twin** of any
    formatter you fix; `formatTooltipCurrency`/`formatTooltipNumber` carried it too.

14. **A string rendered as a number that cannot represent it.** The sibling of 13, same
    function family. `formatCellValue` numeric-formats anything parsing finite, guarded
    only by a NAME-based `isIdentifierColumn` (`_ID`, `_NBR`, `" Code"`…). Measured over
    all 958 text columns in demo25: 430 unmatched by the guard, **8 corrupted**, worst
    being `rpt_gl."GL Account"` — `'01000123923000000000000'` rendered
    "1,000,123,923,000,000,000,000", dropping the leading zero, adding separators, and
    past 2^53 getting the digits themselves wrong. Extending the name list is
    whack-a-mole ("GL Account", "Value", "Hierarchy Path" share no suffix). The rule
    that generalizes: **format a string as a number only when that ROUND-TRIPS**
    (`String(Number(v)) === v.trim()`) — exactly the set where numeric rendering loses
    nothing, needing no knowledge of naming. The name guard still earns its place, since
    `'1358301387'` round-trips and only the name keeps an Account ID out of commas.

15. **A failed query recorded as a VALUE.** `execute_kpi_definition` never raises; it
    returns `error` with `value: None`. The alert runner never read `error`, so
    `evaluate_condition(value=None)` was False (correct: no data never breaches) and the
    runner then wrote `last_state = "ok"`, `last_status = "ok at None"` — an all-clear
    for a query that failed, which also RESET a breached alert so the next working run
    re-notified for a condition that never cleared. Any consumer of a result object
    must check its error field before trusting its value. The sibling: an org whose
    warehouse is not built yet fails EVERY canvas query with ORA-00942, and eight
    surfaces (home, workstream, four explorer routes, NLQ, alerts, schedules) each
    forwarded the driver's text. One detector (`is_missing_relation_error`) and one
    sentence (`WAREHOUSE_NOT_BUILT_NOTE`) now serve all of them — when a class has that
    many surfaces, the fix is a shared helper, not eight edits.

16. **`value or default` swallowing a legitimate zero.** `int(x or 13)` turned
    `hour_utc = 0` (midnight UTC) into 13:00 on both the due check and at creation, so
    a midnight schedule silently ran at 1pm. Found by a test fixture with `hour_utc: 0`
    that was never due at noon. Swept every `or <number>` in api/ (~60): this was the
    ONLY one where 0 is a real value — the rest default a 0-day window or a 0 limit,
    which are meaningless anyway. The rule: `or` is fine when 0 is invalid; when 0 is a
    value, only ABSENCE defaults (`13 if x is None else int(x)`). JS: `??` not `||`.

**How five of these were found: a widely-used export with no test.** Enumerate
`export function` in `lib/`, count references across the app, and subtract anything
named in a `.test.ts`. 44 exports had 3+ uses and no test. That list is where
`prettifyFieldName` (broken for the six legacy orgs it was written for), the three UTC
date builders, and the four coercion bugs in classes 13-14 all came from — and `businessLabels.test.ts` already EXISTED, covering
only the workstream lists, so "there is a test file" proves nothing about a function.

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

**FIXED 2026-09-02** in `build_data_dictionary.primary_date_column`: the pick now reads
`pg_stats.null_frac` and takes the first date column populated on at least 90% of rows,
falling back to field order when none qualifies. The bar is 90% rather than "more than
half" so the answer cannot depend on which database the generator ran against —
RPT_BILL's Window Start Date is 100% null on demo25 and 49.7% null at Ellensburg, so a
50% bar would accept it at one client and reject it at the other. The same function
emits the INDEX, so the offered default and the indexed column stay the same column by
construction. The table above stays: it is the evidence for why the bar exists.

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

    catalog_dbt       0 business_processes,  0 of 38 canvases with process_guides
    (the retired legacy catalog carried 21 processes and guides on every canvas -- the
    content exists in git history and has to be PORTED to the 38 canvases; there is no
    longer a shape where it works by accident)

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
