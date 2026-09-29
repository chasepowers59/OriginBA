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
  `cached_workstream_summary`, `cached_query`) so keys cannot drift. Off under tests and with
  `PORTAL_WARM_CACHE=false`. Its last run per org is in Settings > System health.
- **Date-window contract** `tests/fixtures/date_presets.json`: the browser (`datePresets.ts`) and
  the server (`api/date_presets.py`) must compute the same opening window, or the warmed report is
  never the one asked for. Both suites read this file; add a case there, never in one suite only.
  Catalog presets may be names (`"last_12_months"`): a name picks the chip of that label.

## Measured (say where a number came from)

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
