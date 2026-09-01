# UX / chart review backlog — 2026-08-31 (mediums closed 2026-09-01)

Two review passes (charts, UX/layout) ran over `apps/analytics-portal`. All HIGH
findings and the quick MEDIUMs were fixed the same day; the remaining ten mediums
were burned down on 2026-09-01 (tests-first where the logic was pure):

## Medium — ALL FIXED 2026-09-01

- Tile measure mismatch → `lib/dashboardTileMath.chartedMeasureColumn` (tested):
  the tile charts the FIRST measure's column, matching its label/currency.
- suggestChart ID-column measure → consults `isIdentifierColumn`, samples 20 rows
  for both roles, prefers non-identifier dimensions (`databaseChartUtils.test.ts`).
- VisualPicker guardrails → `lib/visualGuardrails` (tested): pie >30 slices and
  single-series stacked visuals disable with a reason tooltip.
- Tile KPI agg → `kpiHeadline` (tested): sums only sum/count; single ungrouped row
  passes through; grouped avg/min/max shows — instead of a wrong number.
- Menus close on outside click + navigation (AppShell pointerdown listener).
- Pin targets an existing dashboard → PinMenu ("+ New dashboard" / "Add to
  existing"); pins APPEND to the first free slot and never replace; full board
  surfaces an error.
- FieldPill click-to-add (role-routed shelf) + ⠿ grip; Enter works natively.
- × hit-targets padded to ~24px (negative margins keep the chip size).
- Builder data pane: max-h + sticky on lg, 320px cap stacked; save confirmation
  names where views live; save errors render in error styling with role=alert.
- Dashboard save errors surface in an alert banner (catch added).

## Low  — ALL FIXED 2026-09-01

- Heading eyebrows: one class string app-wide (`text-sky-600 dark:text-sky-400`);
  the DQ board's `text-brand` and the build page's inline style are gone.
- Copy: "reporting canvases" no longer appears in user-facing text (the SQL search
  says "Search tables…"); save actions all say "view" ("Save view", "Saved views");
  `fetchJson` now runs `parseApiError` ONCE so every screen shows the message, not
  raw JSON (the SQL workspace's private copy of that parser was deleted).
- Home hero: the primary CTA is Explore (the self-serve spine), the report library
  is secondary; the copy names all three ways in.
- SQL: the Tables tab says what it found ("No table matches …") instead of
  rendering nothing; the paging footer and page intro report the ACTUAL page size
  instead of a hardcoded 50.
- MiniSparkChart: one truncation (`lib/axisLabels.tickLabels`, 4 tests) that falls
  back to head…tail when two labels would render identically.
- Time-series sort verified: both dialects bucket with date_trunc/TRUNC and the API
  serializes via isoformat(), so the bucket labels ARE lexicographically sortable —
  no change needed.
- ExecutiveDashboard failure state has a "Try again" button; the FavoritesPanel
  empty state links to the builder.
- ResultsPanel insight banner is suppressed when the total is <= 0 rather than
  claiming "leads at 0.0% of total".
- "Export to Excel" writes real .xlsx as of the export work — item resolved.
