# Origin_Demo Snapshot Validation Results — 2026-05-21

Script: `sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql`  
Client: `demo` (`PDEMODB_DEMO`, `CISADM`)

## Summary

All seven snapshot tables **passed** grain, row-count, and totals checks. No duplicate natural-key groups. Full-table source vs snapshot counts and additive totals match. Rolling 12-month monthly parity checks show zero row and total deltas for months returned.

Operational maintenance on demo uses a **6-month** rolling window (not 12-month); validators still use a 12-month source comparison window for parity, which passed.

## Per-table results

| Snapshot | Rows | Grain (duplicates) | Full-table source parity | Rolling-window monthly parity |
| --- | ---: | --- | --- | --- |
| FT_RPT_CURR | 62,986 | Pass | Pass | Pass |
| BSEG_BILLED_USAGE_RPT_CURR | 166,078 | Pass | Pass | Pass |
| BSEG_SQ_USAGE_RPT_CURR | 189,885 | Pass | Pass | Pass |
| D1_MSRMT_RPT_CURR | 10,409,822 | Pass | Pass | Pass |
| FT_GL_DISTRIBUTION_RPT_CURR | 108,865 | Pass | Pass | N/A (ultra-fast validator) |
| D1_USAGE_RPT_CURR | 27,462 | Pass | Pass (recent-window slice) | Pass |
| D1_USAGE_SCALAR_DTL_RPT_CURR | 28,844 | Pass | Pass | Pass |

## Notes

- Date coverage spans roughly 2007–2026 (FT) through demo C2M history; D1_MSRMT max business date ~2026-04-14.
- FT_GL net `GL_AMOUNT` is 0 by design (debits/credits balance); `STATISTIC_AMOUNT` parity matched source at 20,203,333.14.
- D1 usage/scalar detail validators confirm preserved rows older than the rolling comparison window (baseline history retained after 6-month cutover).
- No linked bug tickets required from this run.
