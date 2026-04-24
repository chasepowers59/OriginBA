# Latest Active Snapshot Runs

Use this file to store the latest observed runtime capture for the 7 active staggered snapshots.

## Source Query

- [15_latest_active_snapshot_runs.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/impact/15_latest_active_snapshot_runs.sql)

## Capture Date

- `2026-04-24`

## Latest Observed Runs

| Order | Workstream | Table | Latest Observed Source | Actual Start Date | Run Duration | Run Minutes | Notes |
|---|---|---|---|---|---:|---:|---|
| 1 | finance | `FT_RPT_CURR` | Scheduler | `2026-04-24 13:00:00.195891` | `0:03:13` | `3.22` | Latest scheduler run succeeded; next run `2026-04-24 19:00:00.235444` |
| 2 | billing | `BSEG_BILLED_USAGE_RPT_CURR` | Scheduler | `2026-04-24 07:30:00.827796` | `0:05:01` | `5.02` | Rolling 12-month procedure promoted and manually validated on `2026-04-24`; next scheduler run `2026-04-24 13:30:00.858771` |
| 3 | billing | `BSEG_SQ_USAGE_RPT_CURR` | Scheduler | `2026-04-24 08:00:00.268175` | `0:05:37` | `5.62` | Rolling 12-month procedure promoted and manually validated on `2026-04-24`; next scheduler run `2026-04-24 14:00:00.303782` |
| 4 | meter_ops | `D1_MSRMT_RPT_CURR` | Scheduler | `2026-04-24 08:30:00.725294` | `0:04:06` | `4.10` | Rolling 12-month procedure active; next run `2026-04-24 14:30:00.751050` |
| 5 | finance | `FT_GL_DISTRIBUTION_RPT_CURR` | Manual validation refresh | `2026-04-24 13:37:52` | `0:05:53` | `5.89` | Rolling 6-month procedure validated on `2026-04-24`; whole-table parity and preserved 6-to-12-month sanity checks stayed exact |
| 6 | meter_ops | `D1_USAGE_RPT_CURR` | Scheduler | `2026-04-24 09:30:00.981749` | `0:09:31` | `9.52` | Rolling 12-month procedure active; next run `2026-04-24 15:30:00.010991` |
| 7 | meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | Scheduler | `2026-04-24 10:00:00.722861` | `0:07:31` | `7.52` | Rolling 12-month procedure active; next run `2026-04-24 16:00:00.754445` |

## Notes

- Intended for the currently active 7-snapshot stagger only.
- Latest observed runtime may come from either the scheduler history or a manual validation refresh, whichever is newer.
- Update this file after major scheduler or procedure changes.
- Compare against prior captures when validating runtime improvements.
- Manual cutover validation for the two BSEG snapshots on `2026-04-24` completed successfully, but those direct procedure calls do not appear in scheduler history and therefore are not reflected as `Latest Observed Source` rows here.
- `FT_GL_DISTRIBUTION_RPT_CURR` was manually validated again on `2026-04-24` after the maintenance window was reduced from `12` months to `6` months. The next scheduled job should be used to confirm the same improvement under scheduler history.
