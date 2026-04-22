# Latest Active Snapshot Runs

Use this file to store the latest observed runtime capture for the 7 active staggered snapshots.

## Source Query

- [15_latest_active_snapshot_runs.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/impact/15_latest_active_snapshot_runs.sql)

## Capture Date

- `2026-04-22`

## Latest Observed Runs

| Order | Workstream | Table | Latest Observed Source | Actual Start Date | Run Duration | Run Minutes | Notes |
|---|---|---|---|---|---:|---:|---|
| 1 | finance | `FT_RPT_CURR` | Manual validation refresh | `2026-04-22 11:54:55.890809` | `0:01:35` | `1.59` | Rolling 12-month procedure deployed; `814,031` in-window rows reloaded |
| 2 | billing | `BSEG_BILLED_USAGE_RPT_CURR` | Scheduler | `2026-04-22 07:30:00.985523` | `0:05:14` | `5.23` | Next run `2026-04-22 13:30:00.011304` |
| 3 | billing | `BSEG_SQ_USAGE_RPT_CURR` | Scheduler | `2026-04-22 08:00:01.087001` | `0:06:10` | `6.17` | Next run `2026-04-22 14:00:00.132889` |
| 4 | meter_ops | `D1_MSRMT_RPT_CURR` | Manual validation refresh | `2026-04-22 12:08:11.048843` | `0:04:05` | `4.09` | Rolling 12-month procedure deployed; `222,064` in-window rows reloaded |
| 5 | finance | `FT_GL_DISTRIBUTION_RPT_CURR` | Manual validation refresh | `2026-04-22 11:44:50.499107` | `0:09:36` | `9.60` | Rolling 12-month procedure deployed; `1,708,636` in-window rows reloaded |
| 6 | meter_ops | `D1_USAGE_RPT_CURR` | Scheduler | `2026-04-22 09:30:00.383021` | `0:07:54` | `7.90` | Next run `2026-04-22 15:30:00.426512` |
| 7 | meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | Scheduler | `2026-04-22 10:00:00.682940` | `0:09:18` | `9.30` | Next run `2026-04-22 16:00:00.778577` |

## Notes

- Intended for the currently active 7-snapshot stagger only.
- Latest observed runtime may come from either the scheduler history or a manual validation refresh, whichever is newer.
- Update this file after major scheduler or procedure changes.
- Compare against prior captures when validating runtime improvements.
