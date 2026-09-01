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

## Low

- Heading pattern drift (eyebrow+h1 vs plain h1 vs none on Settings); DQ eyebrow uses
  `text-brand`, others `text-sky-600 dark:…`, build page uses an inline style.
- Copy: "canvases"/"snapshot" jargon in user-facing text (AppShell footer text,
  SQL search placeholder, tile editor label); raw `err.message` in builder/explorer
  (adopt DatabaseWorkspace's `parseApiError`); "Export to Excel" produces CSV;
  naming drift Save view / Save to workspace / Saved views / favorites.
- Home hero: two CTAs both go to /reports; neither promotes Explore.
- SQL: no shimmer while executing; Tables tab silent when empty; footer always says
  "50-row paging" regardless of page size.
- MiniSparkChart double truncation (14-char data cut + 8-char tick cut) can make two
  categories indistinguishable on the axis.
- Time-series sort is `localeCompare` on the bucket label — verify the TD0 bucket
  format is ISO-sortable everywhere.
- ExecutiveDashboard terminal failure state has no retry; FavoritesPanel empty state
  doesn't link anywhere.
- `ResultsPanel` insight banner reads "leads at 0.0% of total" when total ≤ 0 —
  suppress instead.
