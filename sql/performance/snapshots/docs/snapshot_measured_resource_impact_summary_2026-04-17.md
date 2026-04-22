# Snapshot Measured Resource Impact Summary

As of `2026-04-17`

## Purpose
This document captures measured database resource evidence for the governed snapshot family using the read-only impact scripts under:

- `sql/performance/snapshots/impact/`

This is intended for both internal planning and client-facing explanation of:

- observed query demand
- observed refresh demand
- estimated data footprint
- configured scheduler cadence
- evidence gaps that still remain

## Evidence used

### Query demand
- `07_snapshot_sql_usage_averages.sql`
- `08_snapshot_sql_usage_share.sql`

### Refresh demand
- `09_snapshot_scheduler_runtime_averages.sql`

### Estimated data footprint
- `11_snapshot_table_stats_density.sql`

### Scheduler cadence
- `12_snapshot_scheduler_configuration.sql`

### Freshness
- `03_snapshot_row_counts_and_freshness.sql`

## Important interpretation rules
- Query cost, refresh cost, and table size are separate dimensions.
- The largest snapshot is not always the most expensive query target.
- Low observed usage in the SQL sample does not prove low intrinsic database cost.
- Blank scheduler rows mean either no visible job under the expected name, no retained history, or a different refresh mechanism.
- Estimated data footprint from optimizer stats is not the same as exact segment storage.

## Measured query demand

Results from `07_snapshot_sql_usage_averages.sql` show the following observed average-per-execution costs.

| Workstream | Snapshot | Executions | Avg Elapsed Sec / Exec | Avg CPU Sec / Exec | Avg Buffer Gets / Exec | Avg Disk Reads / Exec | Interpretation |
|---|---|---:|---:|---:|---:|---:|---|
| meter_ops | `D1_MSRMT_RPT_CURR` | 27 | 569.31 | 230.31 | 9,482,363.74 | 441,167.11 | Slowest average execution time |
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | 38 | 381.97 | 257.11 | 17,001,463.18 | 193,314.58 | Highest average CPU and logical-read pressure |
| finance | `FT_RPT_CURR` | 50 | 241.86 | 148.27 | 10,329,933.94 | 136,713.76 | Material per-execution demand |
| meter_ops | `D1_USAGE_RPT_CURR` | 190 | 209.74 | 89.08 | 6,381,339.57 | 3,795,034.92 | Dominant physical-read hotspot |
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | 346 | 116.81 | 29.68 | 3,120,827.82 | 161,532.44 | Highest execution volume with meaningful sustained demand |
| payments_cashiering | `PAY_TNDR_CASH_RPT_CURR` | 3 | 1.54 | 1.20 | 12,506.33 | 487.00 | Low observed usage in this sample |
| debt_mgmt | `ACCT_DEBT_RPT_CURR` | 3 | 1.54 | 1.20 | 12,506.33 | 487.00 | Low observed usage in this sample |
| debt_mgmt | `COLL_PROC_RPT_CURR` | 3 | 1.54 | 1.20 | 12,506.33 | 487.00 | Low observed usage in this sample |
| billing | `BSEG_SQ_USAGE_RPT_CURR` | 6 | 1.15 | 0.97 | 7,526.83 | 250.17 | Low observed usage in this sample |
| billing | `BSEG_BILLED_USAGE_RPT_CURR` | 6 | 1.15 | 0.97 | 7,526.83 | 250.17 | Low observed usage in this sample |

### Query-demand conclusions
- `D1_MSRMT_RPT_CURR` has the worst observed average elapsed time per execution.
- `FT_GL_DISTRIBUTION_RPT_CURR` has the highest observed average CPU and logical-read demand per execution.
- `D1_USAGE_RPT_CURR` is the dominant observed physical-read consumer by a large margin.
- `D1_USAGE_SCALAR_DTL_RPT_CURR` has the highest observed execution volume and therefore remains a major sustained workload consumer even though its per-execution average is lower than the top three.
- Observed query demand is concentrated in `meter_ops` and `finance`.

## Relative workload share

Results from `08_snapshot_sql_usage_share.sql` show how the observed workload is distributed within the current snapshot family sample.

| Workstream | Snapshot | Total Executions | Total Elapsed Seconds | Total CPU Seconds | Total Buffer Gets Millions | Total Disk Reads Millions | CPU Share % | Logical I/O Share % | Physical I/O Share % |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| meter_ops | `D1_USAGE_RPT_CURR` | 194 | 39,854.97 | 16,929.46 | 1,212.52 | 721.06 | 33.42 | 32.67 | 89.79 |
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | 350 | 40,421.63 | 10,273.09 | 1,079.87 | 55.89 | 20.28 | 29.09 | 6.96 |
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | 42 | 14,518.59 | 9,773.71 | 646.12 | 7.35 | 19.29 | 17.41 | 0.91 |
| finance | `FT_RPT_CURR` | 54 | 12,096.67 | 7,417.14 | 516.56 | 6.84 | 14.64 | 13.92 | 0.85 |
| meter_ops | `D1_MSRMT_RPT_CURR` | 31 | 15,375.08 | 6,222.04 | 256.09 | 11.91 | 12.28 | 6.90 | 1.48 |
| billing | `BSEG_SQ_USAGE_RPT_CURR` | 10 | 10.67 | 9.45 | 0.11 | 0.00 | 0.02 | 0.00 | 0.00 |
| billing | `BSEG_BILLED_USAGE_RPT_CURR` | 10 | 10.67 | 9.45 | 0.11 | 0.00 | 0.02 | 0.00 | 0.00 |
| debt_mgmt | `COLL_PROC_RPT_CURR` | 7 | 8.37 | 7.22 | 0.10 | 0.00 | 0.01 | 0.00 | 0.00 |
| payments_cashiering | `PAY_TNDR_CASH_RPT_CURR` | 6 | 7.95 | 6.80 | 0.10 | 0.00 | 0.01 | 0.00 | 0.00 |
| debt_mgmt | `ACCT_DEBT_RPT_CURR` | 7 | 8.37 | 7.22 | 0.10 | 0.00 | 0.01 | 0.00 | 0.00 |

### Relative-share conclusions
- `D1_USAGE_RPT_CURR` is the dominant physical I/O consumer, accounting for `89.79%` of observed physical reads in the reviewed sample.
- `D1_USAGE_RPT_CURR` and `D1_USAGE_SCALAR_DTL_RPT_CURR` together account for over half of observed CPU share and over `61%` of observed logical I/O share.
- `FT_GL_DISTRIBUTION_RPT_CURR` and `FT_RPT_CURR` together contribute a meaningful share of CPU and logical I/O, but very little physical I/O relative to `D1_USAGE_RPT_CURR`.
- `meter_ops` is the dominant workload family by both sustained execution volume and resource share.

## Measured refresh demand

Results from `09_snapshot_scheduler_runtime_averages.sql` show the following observed refresh runtimes.

| Workstream | Snapshot | Observed Runs | Avg Run Seconds | Median Run Seconds | Max Run Seconds | Interpretation |
|---|---|---:|---:|---:|---:|---|
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | 4 | 14,194.50 | 14,133.50 | 15,267.00 | Dominant refresh-window cost |
| meter_ops | `D1_USAGE_RPT_CURR` | 16 | 2,336.63 | 2,562.50 | 3,086.00 | Secondary meter-ops refresh cost |
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | 32 | 1,229.88 | 1,079.50 | 1,855.00 | Moderate refresh demand |
| meter_ops | `D1_MSRMT_RPT_CURR` | 16 | 903.63 | 881.00 | 1,154.00 | Meaningful but lower than usage snapshots |
| finance | `FT_RPT_CURR` | 64 | 376.44 | 378.00 | 487.00 | Lowest observed runtime among visible active jobs |

### Refresh-demand conclusions
- `D1_USAGE_SCALAR_DTL_RPT_CURR` is the heaviest refresh job by far at about `3.94` hours average runtime.
- `D1_USAGE_RPT_CURR` is the next material refresh consumer at about `38.9` minutes average runtime.
- Finance refresh cost is materially lower than the two main meter-ops refreshes.
- Meter operations is the dominant refresh-window consumer overall.

## Estimated data footprint

Results from `11_snapshot_table_stats_density.sql` show estimated data size from `NUM_ROWS * AVG_ROW_LEN`.

| Snapshot | Num Rows | Avg Row Len | Last Analyzed | Estimated Data MB | Interpretation |
|---|---:|---:|---|---:|---|
| `FT_GL_DISTRIBUTION_RPT_CURR` | 4,954,580 | 690 | 17-APR-26 | 3,260.29 | Largest estimated payload |
| `D1_MSRMT_RPT_CURR` | 1,680,216 | 1,022 | 17-APR-26 | 1,637.63 | Large and wide |
| `FT_RPT_CURR` | 4,856,125 | 352 | 17-APR-26 | 1,630.17 | Large row count, moderate width |
| `BSEG_SQ_USAGE_RPT_CURR` | 3,745,478 | 396 | 16-APR-26 | 1,414.50 | Large billing detail payload |
| `BSEG_BILLED_USAGE_RPT_CURR` | 2,214,878 | 454 | 16-APR-26 | 958.97 | Large billing header payload |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | 720,071 | 978 | 17-APR-26 | 671.61 | Moderate size but heavy refresh/query usage |
| `D1_USAGE_RPT_CURR` | 684,214 | 924 | 17-APR-26 | 602.93 | Moderate size with high physical-read demand |
| `PAY_TNDR_CASH_RPT_CURR` | 648,916 | 277 | 14-APR-26 | 171.42 | Mid-volume, low observed usage |
| `COLL_PROC_RPT_CURR` | 44,444 | 504 | 09-APR-26 | 21.36 | Small estimated footprint |
| `ACCT_DEBT_RPT_CURR` | 11,452 | 243 | 09-APR-26 | 2.65 | Small estimated footprint |

### Footprint conclusions
- `FT_GL_DISTRIBUTION_RPT_CURR` is both large and expensive.
- `D1_MSRMT_RPT_CURR` is large and has the worst observed average query runtime.
- `D1_USAGE_RPT_CURR` and `D1_USAGE_SCALAR_DTL_RPT_CURR` are not the largest tables, but they still drive a disproportionate share of observed runtime pressure.
- Table size alone is not a sufficient proxy for database demand.

## Configured scheduler cadence

Results from `12_snapshot_scheduler_configuration.sql` show visible configured jobs and cadence.

| Workstream | Snapshot | Job Name | Enabled | State | Repeat Interval | Last Start | Next Run |
|---|---|---|---|---|---|---|---|
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | `JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=HOURLY;INTERVAL=6` | 17-APR-26 01:13 GMT | 17-APR-26 07:13 GMT |
| finance | `FT_RPT_CURR` | `JOB_REFRESH_FT_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=HOURLY;INTERVAL=6` | 17-APR-26 10:26 GMT | 17-APR-26 04:26 GMT |
| meter_ops | `D1_MSRMT_RPT_CURR` | `JOB_REFRESH_D1_MSRMT_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=HOURLY;INTERVAL=6` | 17-APR-26 12:53 GMT | 17-APR-26 06:53 GMT |
| meter_ops | `D1_USAGE_RPT_CURR` | `JOB_REFRESH_D1_USAGE_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=HOURLY;INTERVAL=6` | 17-APR-26 12:52 GMT | 17-APR-26 06:52 GMT |
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | `JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=DAILY;BYHOUR=3;BYMINUTE=30;BYSECOND=0` | 17-APR-26 03:30 GMT | 18-APR-26 03:30 GMT |

No visible configured job rows were returned in this sample for:

- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `ACCT_DEBT_RPT_CURR`
- `COLL_PROC_RPT_CURR`
- `PAY_TNDR_CASH_RPT_CURR`

### Scheduler conclusions
- Finance and the main meter snapshots are actively scheduled and visible.
- The two-hourly-expression snapshots observed here actually run every `6` hours based on the configured interval.
- `D1_USAGE_SCALAR_DTL_RPT_CURR` is isolated to a daily run, which aligns with its materially higher refresh cost.

## Freshness and row counts

Results from `03_snapshot_row_counts_and_freshness.sql` show current row counts and visible `LOAD_DTTM` recency.

| Workstream | Snapshot | Row Count | Min Load DTTM | Max Load DTTM | Freshness Interpretation |
|---|---|---:|---|---|---|
| billing | `BSEG_BILLED_USAGE_RPT_CURR` | 2,214,878 | 10-APR-26 01:36 GMT | 10-APR-26 01:36 GMT | Stale relative to current date |
| billing | `BSEG_SQ_USAGE_RPT_CURR` | 3,745,478 | 10-APR-26 01:42 GMT | 10-APR-26 01:42 GMT | Stale relative to current date |
| finance | `FT_RPT_CURR` | 4,856,125 | 17-APR-26 10:26 GMT | 17-APR-26 10:26 GMT | Fresh and aligned with active scheduler |
| finance | `FT_GL_DISTRIBUTION_RPT_CURR` | 4,954,580 | 17-APR-26 01:13 GMT | 17-APR-26 01:13 GMT | Fresh and aligned with active scheduler |
| debt_mgmt | `ACCT_DEBT_RPT_CURR` | 11,452 | 08-APR-26 12:50 GMT | 08-APR-26 12:50 GMT | Stale relative to current date |
| debt_mgmt | `COLL_PROC_RPT_CURR` | 44,444 | 08-APR-26 12:28 GMT | 08-APR-26 12:28 GMT | Stale relative to current date |
| meter_ops | `D1_USAGE_RPT_CURR` | 684,214 | 17-APR-26 12:52 GMT | 17-APR-26 01:33 GMT | Fresh; multiple load timestamps visible within the current refresh cycle |
| meter_ops | `D1_USAGE_SCALAR_DTL_RPT_CURR` | 720,071 | 17-APR-26 07:00 GMT | 17-APR-26 07:10 GMT | Fresh; narrow intra-run spread visible |
| meter_ops | `D1_MSRMT_RPT_CURR` | 1,680,216 | 17-APR-26 12:53 GMT | 17-APR-26 12:53 GMT | Fresh and aligned with active scheduler |
| payments_cashiering | `PAY_TNDR_CASH_RPT_CURR` | 648,916 | 08-APR-26 02:56 GMT | 08-APR-26 02:56 GMT | Stale relative to current date |

### Freshness conclusions
- Finance and meter-ops snapshots appear operationally current as of `2026-04-17`.
- Billing, debt-management, and payments snapshots appear stale in the reviewed sample because their latest visible `LOAD_DTTM` values are between `2026-04-08` and `2026-04-10`.
- The stale groups also correspond to the snapshots that did not show visible scheduler configuration rows in the current sample.
- Business clarification: these stale snapshots are intentionally not being refreshed at this time, so the observed staleness is expected and should not be treated as an operational failure.
- `D1_USAGE_RPT_CURR` and `D1_USAGE_SCALAR_DTL_RPT_CURR` show multiple same-day load timestamps rather than one single timestamp for the whole table, which is consistent with batch-written `LOAD_DTTM` patterns during refresh.

## Overall resource-planning conclusions

### Highest sustained database concern
`meter_ops` is the dominant overall database concern because it combines:

- the heaviest refresh-window cost
- the highest physical-read demand
- the highest execution volume

### Highest per-execution concern
The highest-cost single execution patterns are:

1. `D1_MSRMT_RPT_CURR` for average elapsed time
2. `FT_GL_DISTRIBUTION_RPT_CURR` for average CPU and logical I/O
3. `D1_USAGE_RPT_CURR` for average physical I/O

### Largest estimated data footprint
The largest estimated snapshot payloads are:

1. `FT_GL_DISTRIBUTION_RPT_CURR`
2. `D1_MSRMT_RPT_CURR`
3. `FT_RPT_CURR`
4. `BSEG_SQ_USAGE_RPT_CURR`
5. `BSEG_BILLED_USAGE_RPT_CURR`

### End-user performance
Current user-facing report and dashboard load times are reported to be within `15 seconds`.

Interpretation:
- This is materially better than the prior live-join model that motivated the snapshot transition.
- Database-side workload is still worth monitoring, but current user-facing performance is within an acceptable interactive range.
- End-user timing should still be captured against named reports or dashboard pages if a formal client appendix is needed later.

## Recommended operational stance
1. Treat `meter_ops` as the primary capacity-planning workstream.
2. Keep `D1_USAGE_SCALAR_DTL_RPT_CURR` on a controlled off-peak refresh window.
3. Watch `D1_USAGE_RPT_CURR` closely for physical I/O pressure.
4. Watch `FT_GL_DISTRIBUTION_RPT_CURR` closely for CPU and logical-read pressure.
5. Do not assume the low-observed-usage workstreams are intrinsically cheap without a broader observation window.

## Remaining evidence gaps

The following information is still missing or incomplete:

### 1. Exact segment storage
Missing:
- exact table segment MB
- exact index segment MB

Reason:
- `10_snapshot_storage_footprint_summary.sql` failed with `ORA-00942` on `ALL_SEGMENTS`

Status:
- `11_snapshot_table_stats_density.sql` provides estimated data size instead
- `10b_snapshot_storage_footprint_user_views_fallback.sql` can be used if connected directly as `CISADM`

### 2. Current freshness by `LOAD_DTTM`
Resolved:
- freshness evidence has now been captured from `03_snapshot_row_counts_and_freshness.sql`

Remaining concern:
- several snapshots are measurably stale in the current sample, but the business has confirmed that this is intentional for the currently paused workstreams

### 3. Visibility for missing scheduler jobs
Missing:
- confirmation of whether blank scheduler rows represent no job, hidden job, or alternate refresh mechanism

Affected snapshots:
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `ACCT_DEBT_RPT_CURR`
- `COLL_PROC_RPT_CURR`
- `PAY_TNDR_CASH_RPT_CURR`

Observed consequence:
- these same snapshots also appear stale by `LOAD_DTTM`, but that staleness is currently intentional

### 4. End-user BI/report load times
Partially resolved:
- current end-user load times are reported to be within `15 seconds`

Still missing for formal evidence:
- named report-by-report timings
- test method and sample scope
- side-by-side comparison with legacy live-join reporting

Value:
- would translate DB-side evidence into user-facing performance proof

## Suggested next test order
1. Run `08_snapshot_sql_usage_share.sql`
2. Run `10b_snapshot_storage_footprint_user_views_fallback.sql` if connected as `CISADM`
3. Determine whether exact segment storage can be collected from a CISADM or DBA-capable session
4. Capture named BI tool load times if a formal client appendix is required
