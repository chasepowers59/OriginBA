---
name: originba-portal-performance
description: How the Origin BA portal stays fast without ever serving a stale or different number — the warehouse build stamp, the versioned result cache, the background warmer, the shared date-window contract, and the measurements behind them. Load before changing caching, query routing, date presets, or anything that makes pages faster.
---

# Portal performance: fast, never wrong

## The rule

A faster answer must be the SAME answer. Every speed-up here is keyed to the data it came
from and falls back to the slow, correct path when unsure.

## Pieces

- **Build stamp** `api/data_version.py`: per org, changes whenever dbt rebuilds or merges into a
  reporting table. Postgres: each reporting table's oid + relfilenode + insert/update/delete
  counters (a table rebuild is a new table; the incremental merge into rpt_billed_charge moves
  the counters). Oracle: max(last_analyzed), max(last_ddl_time), count over ORIGINBA_REPORTING
  (every model build gathers statistics). Read at most once a minute; `None` if unreadable.
  Proven on the 5433 fixture: stable at rest, moves on a rebuild.
- **Result cache** `api/summary_cache.py`: key includes today's date AND the stamp; kept until
  the stamp moves (cap 12 h), 5 min without a stamp. Summaries with a failed card are never kept.
- **Warmer** `api/cache_warmer.py`: a thread per API process; every minute, when an org's stamp
  is new, builds home + each workstream summary (30 days, no compare, all workstreams, no row
  rules) and each canvas of >= 1M rows' OPENING report (first premade report over the canvas's
  default window), through the routes' own functions (`cached_home_summary`,
  `cached_workstream_summary`, `cached_query`) so keys cannot drift. Also the compare-mode home
  summary ("ori findings") and the cards' 36-month history ("ori trends", `api/ori_series.py`:
  one monthly query per windowed card, ~6-10 s cold on Ellensburg, 35 ms warm). Off under tests and with
  `PORTAL_WARM_CACHE=false`. Its last run per org is in Settings > System health.
- **`data_as_of` anchor** (`config/portal_organizations.json`, `api/reporting_dates.py`): a frozen TEST
  copy declares the last day ALL of its activity was normal (measure bills, payments AND transactions
  by day; CityCorp's first anchor, read from bills alone, sat six weeks past the real end). Relative
  windows end there, Ori's history ends there, and Data Quality takes the build-to-anchor gap off every
  "Days ..." column (`api/dq_routes.aging_gap_days`), since the canvases age to the BUILD date. Remove
  the key when the copy is refreshed.
- **Date-window contract** `tests/fixtures/date_presets.json`: the browser (`datePresets.ts`) and
  the server (`api/date_presets.py`) must compute the same opening window, or the warmed report is
  never the one asked for. Both suites read this file; add a case there, never in one suite only.
  Catalog presets may be names (`"last_12_months"`): a name picks the chip of that label.

## Measured (say where a number came from)
- Both proof-of-concept organizations, 2026-10-02, through the running API after a restart and
  warm (`scratchpad timing_pass.py`, one request each): Home 30 days 0.04 s warm (4.0 s the first
  time at Ellensburg); the 90-day and 6-month chips 1.4-1.8 s cold, 0.04 s again, with or without
  Compare, so the warmer need not pre-build them; every workstream summary 0.03 s warm at CityCorp
  and 0.65-1.0 s at Ellensburg (cashiering 5.9 s once); Ori findings/trends and Data Quality 0.03-2.2 s
  warm; a 12-month monthly count on each of the eight largest data sets 0.4-1.2 s (rpt_bill_segment_read
  3.0 s at Ellensburg, the one without an aggregate). The 365-day Compare summary is 32-47 s cold and
  is no UI chip; `check_kpi_consistency_live.py` is its only caller. Ori, one live question per
  organization: 10-17 s, four model turns, ~22-25K cached input tokens read and ~11K written per
  organization's first question.

- Ellensburg, 2026-09-29 after the full refresh, every ready-to-run report on the eight
  largest data sets over a 12-month window, cold: 24 of 26 answer in 0.05-1.7 s. The two
  exceptions are OPENING reports: rpt_billed_charge "billed by customer class" 58.5 s and
  rpt_gl "not yet reached the GL" 50.8 s cold, 30 ms and 45 ms warm. The warmer builds both
  after every rebuild; agg_billed_charge_daily (routed once built and proven) takes the first
  off the canvas; an aggregate by GL Distribution Status + Accounting Date is the candidate
  for the second.

- Ellensburg (Oracle in-database, 2.47M bill segments): opening report 0.6-0.8 s over 180 days,
  0.7-0.8 s over 365; the first query after an API restart 11.5 s cold; rpt_billed_charge's
  opening report ~25 s cold (2026-09-28) and ~0.7 s served warm. Full warm of Ellensburg: 20
  pages in ~28 s.
- Stamp read ~150 ms on demo25 Postgres.

## Next: pre-aggregates

Only with exactness proven per client build (aggregate totals == canvas totals as dbt tests,
routed == unrouted as portal tests, non-additive measures never routed, row-security columns
carried or the query goes to the canvas). Design: the pre-aggregates plan in the dbt repo's docs
(see docs/LARGE_CLIENT_SCALE_PLAN.md section 5).
