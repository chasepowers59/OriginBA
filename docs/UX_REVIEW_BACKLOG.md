# UX / chart review backlog — 2026-08-31

Two review passes (charts, UX/layout) ran over `apps/analytics-portal`. All HIGH
findings and the quick MEDIUMs were fixed the same day (see commits "Chart review
fixes…" and "UX review fixes…"). What remains, ranked, so nothing silently drops:

## Medium

- **Tile measure mismatch** — `DashboardTile.tsx` charts the LAST result column but
  takes label + currency from `measures[0]`; a 2-measure premade report labels one
  measure with the other's name. Derive label/currency from the charted column.
- **suggestChart can pick an ID column as measure** — `lib/databaseChartUtils.ts`
  takes the first ≥60%-numeric column; `ACCT_ID` qualifies (bars of summed account
  ids). Consult `isIdentifierColumn`, and sample >1 row when picking the dimension.
- **VisualPicker guardrails** — pie with 200 categories / stacked-* with one series
  are selectable; disable or warn based on row/series count.
- **Tile KPI total sums regardless of agg** — a tile aggregated by avg/min/max shows
  the SUM of group values as its headline. Only total sum/count aggs.
- **User + mobile menus don't close on outside click** — native `<details>` behaviour;
  close on blur/outside click/navigation.
- **Pin can't target an existing dashboard** — pinning always starts a fresh board and
  a second pin replaces the first (unless saved between). Append to the first free
  slot; offer "add to existing" now the dashboards list exists.
- **FieldPill is drag-only** — no click-to-add fallback, no keyboard sensor, no grip
  affordance. Add onClick → role-appropriate shelf + a ⠿ grip (SlotCell has the
  pattern); wire dnd-kit's KeyboardSensor.
- **Tiny × hit-targets** — shelf chips and GlobalFilterBar remove buttons are bare
  text `×` (well under 24px) beside selects; add padding (`p-1 -m-1`).
- **Builder data pane** — fixed `h-[560px]` stacks awkwardly below `lg` and can't
  shrink on short laptops; use max-h + sticky. Save-view confirmation doesn't say
  where views live, and save ERRORS render in the success-styled slot.
- **Dashboard save/load has no error surfacing** — `save()` try/finally without
  catch; `fetchDashboard`/`fetchSnapshots` in the editor likewise. Surface a toast.

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
