# SmartCity Client Snapshot Rollout Status - 2026-04-30

## Purpose

Track the current rollout state for the active 7 SmartCity snapshot tables across
client test databases. This file documents what has been done, what has been
validated, and what is intentionally being held until each client is confirmed.

## Active Snapshot Scope

- `FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

## Current Scheduling Decision

Do not create the recurring 6-hour operational schedules yet.

Recurring schedules should only be applied after a client has:

- all 7 one-time full-history baseline jobs completed successfully
- high-level QA confirming populated tables and preserved snapshot grain
- any known failures remediated and retested
- explicit confirmation that the client is ready for rolling-window cutover

The one-time full-history baseline jobs are separate from the future recurring
6-hour rolling-refresh jobs.

## Client Summary

| Client | Baseline State | High-Level QA State | 6-Hour Schedule State | Notes |
| --- | --- | --- | --- | --- |
| Citycorp | Complete: all 7 succeeded | Passed high-level QA | Pending 6-month rolling cutover | Use 6-month operational procedures and standard 6-hour stagger |
| Fond Du Lac | Complete: all 7 succeeded | Passed high-level QA | Not scheduled | QA variance resolved: `D1_USAGE_SCALAR_DTL` raw-source delta was orphan rows without parent `D1_USAGE`; joined-source parity is exact |
| Newark | Complete: all 7 succeeded | Passed high-level QA | Not scheduled | Source-parity checks now complete for all 7 snapshots, including `BSEG_SQ` and scalar detail |
| College Station | Complete: all 7 succeeded | Passed high-level QA | Not scheduled | Source-parity checks complete for all 7 snapshots, including scalar detail parity (`146` duplicate groups mirrored in source) |
| Ellensburg | Reference environment | Previously tested reference | Existing/reference state only | Not part of this fresh rollout batch |

## Citycorp Completed Baseline Results

All 7 one-time full-history baseline jobs completed successfully.

| Snapshot | Job Result | Runtime | Rows Loaded | Duplicate Grain Groups |
| --- | --- | ---: | ---: | ---: |
| `FT_RPT_CURR` | `SUCCEEDED` | `0:08:24` | `5,769,041` | `0` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `SUCCEEDED` | `0:10:50` | `2,794,760` | `0` |
| `BSEG_SQ_USAGE_RPT_CURR` | `SUCCEEDED` | `0:19:33` | `6,424,723` | `0` |
| `D1_MSRMT_RPT_CURR` | `SUCCEEDED` | `0:10:29` | `1,163,217` | `0` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `SUCCEEDED` | `0:28:22` | `5,029,240` | `0` |
| `D1_USAGE_RPT_CURR` | `SUCCEEDED` | `0:26:32` | `551,683` | `0` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `SUCCEEDED` | `0:12:52` | `546,088` | `0` |

### Citycorp Load Freshness

| Snapshot | Min Load Timestamp | Max Load Timestamp |
| --- | --- | --- |
| `FT_RPT_CURR` | `2026-04-30 12:26:02.915552` | `2026-04-30 12:26:02.915552` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `2026-04-30 12:41:08.348007` | `2026-04-30 12:41:08.348007` |
| `BSEG_SQ_USAGE_RPT_CURR` | `2026-04-30 12:56:03.884400` | `2026-04-30 12:56:03.884400` |
| `D1_MSRMT_RPT_CURR` | `2026-04-30 13:11:07.741178` | `2026-04-30 13:11:07.741178` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `2026-04-30 13:26:08.191665` | `2026-04-30 13:26:08.191665` |
| `D1_USAGE_RPT_CURR` | `2026-04-30 13:41:25.649934` | `2026-04-30 14:06:10.504434` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `2026-04-30 13:56:15.418973` | `2026-04-30 13:56:15.418973` |

### Citycorp Business-Date Coverage And Totals

| Snapshot | Min Business Date | Max Business Date | Total 1 | Total 2 |
| --- | --- | --- | ---: | ---: |
| `FT_RPT_CURR` | `1989-11-03` | `2026-03-25` | `1,496,208.11` | `958,601.48` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `1989-11-03` | `2026-03-11` | `15,711,596,616` | `142,861,336.34` |
| `BSEG_SQ_USAGE_RPT_CURR` | `2018-01-01` | `2026-03-11` | `15,711,596,616` | `15,711,596,616` |
| `D1_MSRMT_RPT_CURR` | `2018-01-02` | `2026-03-11 23:00:00` | `18,727,393` | |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `2024-06-02` | `2026-03-25` | `0` | `0` |
| `D1_USAGE_RPT_CURR` | `2021-08-20` | `2026-03-04 05:44:59` | | |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `2024-03-01` | `2026-03-04 05:44:59` | `9,826,558` | `9,826,558` |

For `FT_GL_DISTRIBUTION_RPT_CURR`, the net GL amount is `0` because debits and
credits balance. This was checked separately:

- rows loaded: `5,029,240`
- rows with non-zero `GL_AMOUNT`: `5,029,240`
- absolute GL amount total: `191,224,499.44`
- statistic amount rows: `0`

## Partial Client Results Captured So Far

### Fond Du Lac

Successful baseline jobs at last check:

- `FT_RPT_CURR`: `SUCCEEDED`, runtime `0:02:33`
- `BSEG_BILLED_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `0:07:12`
- `BSEG_SQ_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `0:36:08`
- `D1_MSRMT_RPT_CURR`: `SUCCEEDED`, runtime `0:07:01`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `SUCCEEDED`, runtime `0:10:54`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `SUCCEEDED`, runtime `1:30:43`
- `D1_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `7:12:06`

Still running at last check:

- none

Completed-table checks captured earlier:

- `FT_RPT_CURR`: `224,870` rows, duplicate `FT_ID` groups `0`
- `BSEG_BILLED_USAGE_RPT_CURR`: `1,529,590` rows, duplicate `BSEG_ID` groups `0`

### Fond Du Lac High-Level QA (latest)

Job history gate:

- all 7 baseline one-time jobs now show `SUCCEEDED` with `RUN_COUNT = 1`, `FAILURE_COUNT = 0`

Row-count source parity check:

- `FT_RPT_CURR`: source `224,870`, snapshot `224,870` (match)
- `BSEG_BILLED_USAGE_RPT_CURR`: source `1,529,590`, snapshot `1,529,590` (match)
- `BSEG_SQ_USAGE_RPT_CURR`: source `2,403,699`, snapshot `2,403,699` (match)
- `D1_MSRMT_RPT_CURR`: source `547,745`, snapshot `547,745` (match)
- `FT_GL_DISTRIBUTION_RPT_CURR`: source `407,515`, snapshot `407,515` (match)
- `D1_USAGE_RPT_CURR`: source `2,865,877`, snapshot `2,865,877` (match)
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: raw source `2,933,947`, snapshot `2,933,836` (explained below); joined-source parity is exact

Duplicate grain-group check (snapshot):

- `FT_RPT_CURR`: `0`
- `BSEG_BILLED_USAGE_RPT_CURR`: `0`
- `BSEG_SQ_USAGE_RPT_CURR`: `0`
- `D1_MSRMT_RPT_CURR`: `0`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `0`
- `D1_USAGE_RPT_CURR`: `0`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `37,121` duplicate `(D1_USAGE_ID, SEQ_NUM)` groups

Duplicate natural-key groups source vs snapshot for scalar detail:

- raw source: `37,159`
- snapshot: `37,121`
- joined-source (`D1_USAGE_SCALAR_DTL` joined to parent `D1_USAGE`): `37,121` (exact snapshot parity)

Root cause analysis for the earlier scalar variance:

- `111` raw scalar-detail rows are orphans with no parent row in `D1_USAGE` (`53` orphan `D1_USAGE_ID`, `73` orphan `(D1_USAGE_ID, SEQ_NUM)` groups).
- Snapshot row-set matches the joined source exactly:
  - joined-source rows: `2,933,836`
  - snapshot rows: `2,933,836`
  - joined-source duplicate groups: `37,121`
  - snapshot duplicate groups: `37,121`

QA disposition:

- `Fond Du Lac` high-level QA now **passes** for baseline readiness.
- Keep 6-hour schedules un-applied until explicit rolling-window cutover approval (per rollout gating).

### Newark

Successful baseline jobs at last check:

- `FT_RPT_CURR`: `SUCCEEDED`, runtime `0:30:13`
- `BSEG_SQ_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `1:02:27`
- `D1_MSRMT_RPT_CURR`: `SUCCEEDED`, runtime `0:42:17`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `SUCCEEDED`, runtime `6:10:40`
- `BSEG_BILLED_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `7:20:12` (retry run)
- `D1_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `19:47:50`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `SUCCEEDED`, runtime `13:03:54`

Still running at latest check:

- none

Known issue:

- `BSEG_BILLED_USAGE_RPT_CURR` previously failed with `ORA-01652 unable to extend temp segment by 128 in tablespace TEMP`.
- The full-history BSEG billed procedure was changed to month-batched loading.
- The retry has now `SUCCEEDED` (`7:20:12`) after the earlier failed attempt (`0:47:27`).

Completed-table checks captured earlier:

- `FT_RPT_CURR`: `10,462,269` rows, duplicate `FT_ID` groups `0`

### Newark High-Level QA (latest)

Job history gate:

- all 7 baseline one-time jobs now show `SUCCEEDED` with `RUN_COUNT = 1`, `FAILURE_COUNT = 0`
- `BSEG_BILLED_USAGE_RPT_CURR` shows both historical `FAILED` and successful retry; latest run is `SUCCEEDED` (`7:20:12`)

Snapshot row-count and freshness capture:

- `FT_RPT_CURR`: `10,462,269` rows, load `2026-04-30 11:43:58.826066`
- `BSEG_BILLED_USAGE_RPT_CURR`: `13,988,815` rows, load window `2026-04-30 15:03:12.419288` to `2026-04-30 22:20:04.995366`
- `BSEG_SQ_USAGE_RPT_CURR`: `26,819,949` rows, load `2026-04-30 12:13:59.293626`
- `D1_MSRMT_RPT_CURR`: `5,018,644` rows, load `2026-04-30 12:29:02.613355`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `16,560,500` rows, load `2026-04-30 12:44:04.125710`
- `D1_USAGE_RPT_CURR`: `13,983,942` rows, load window `2026-04-30 13:08:56.828645` to `2026-05-01 08:40:22.427632`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `14,264,387` rows, load `2026-04-30 13:14:11.274814`

Duplicate grain-group checks (snapshot):

- `FT_RPT_CURR`: `0`
- `BSEG_BILLED_USAGE_RPT_CURR`: `0`
- `BSEG_SQ_USAGE_RPT_CURR`: `0`
- `D1_MSRMT_RPT_CURR`: `0`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `0`
- `D1_USAGE_RPT_CURR`: `0`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `299` duplicate `(D1_USAGE_ID, SEQ_NUM)` groups

Source-row parity checks completed:

- `FT_RPT_CURR`: source `10,462,269`, snapshot `10,462,269` (match)
- `BSEG_BILLED_USAGE_RPT_CURR`: source `13,988,815`, snapshot `13,988,815` (match)
- `BSEG_SQ_USAGE_RPT_CURR`: source grouped grain `26,819,949`, snapshot `26,819,949` (match)
- `D1_MSRMT_RPT_CURR`: source `5,018,644`, snapshot `5,018,644` (match)
- `FT_GL_DISTRIBUTION_RPT_CURR`: source `16,560,500`, snapshot `16,560,500` (match)
- `D1_USAGE_RPT_CURR`: source `13,983,942`, snapshot `13,983,942` (match)
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: source raw `14,264,387`, source joined `14,264,387`, snapshot `14,264,387` (exact parity)

Scalar-detail duplicate-grain parity:

- source raw duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `299`
- source joined duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `299`
- snapshot duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `299`

QA disposition:

- `Newark` high-level QA now **passes** for baseline readiness.
- Keep 6-hour schedules un-applied until explicit rolling-window cutover approval (per rollout gating).

### College Station

Successful baseline jobs at last check:

- `FT_RPT_CURR`: `SUCCEEDED`, runtime `0:44:22`
- `BSEG_BILLED_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `2:28:47`
- `BSEG_SQ_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `2:18:32`
- `D1_MSRMT_RPT_CURR`: `SUCCEEDED`, runtime `1:51:19`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `SUCCEEDED`, runtime `3:12:52`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `SUCCEEDED`, runtime `13:32:17`
- `D1_USAGE_RPT_CURR`: `SUCCEEDED`, runtime `1 day, 1:28:34`

Still running at last check:

- none

No failed jobs were reported at latest check.

### College Station High-Level QA (latest)

Job history gate:

- all 7 baseline one-time jobs now show `SUCCEEDED` with `RUN_COUNT = 1`, `FAILURE_COUNT = 0`

Snapshot row-count and freshness capture:

- `FT_RPT_CURR`: `13,060,469` rows, load `2026-04-30 12:25:58.970493`
- `BSEG_BILLED_USAGE_RPT_CURR`: `14,375,241` rows, load `2026-04-30 12:41:01.520183`
- `BSEG_SQ_USAGE_RPT_CURR`: `16,206,878` rows, load `2026-04-30 12:56:00.157054`
- `D1_MSRMT_RPT_CURR`: `7,654,750` rows, load `2026-04-30 13:11:02.919548`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `27,708,613` rows, load `2026-04-30 13:26:04.014233`
- `D1_USAGE_RPT_CURR`: `2,478,947` rows, load window `2026-04-30 13:45:12.485370` to `2026-05-01 15:06:46.148780`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `3,746,859` rows, load `2026-04-30 13:56:10.567676`

Duplicate grain-group checks (snapshot):

- `FT_RPT_CURR`: `0`
- `BSEG_BILLED_USAGE_RPT_CURR`: `0`
- `BSEG_SQ_USAGE_RPT_CURR`: `0`
- `D1_MSRMT_RPT_CURR`: `0`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `0`
- `D1_USAGE_RPT_CURR`: `0`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `146` duplicate `(D1_USAGE_ID, SEQ_NUM)` groups

Source-row parity checks completed:

- `FT_RPT_CURR`: source `13,060,469`, snapshot `13,060,469` (match)
- `BSEG_BILLED_USAGE_RPT_CURR`: source `14,375,241`, snapshot `14,375,241` (match)
- `BSEG_SQ_USAGE_RPT_CURR`: source grouped grain `16,206,878`, snapshot `16,206,878` (match)
- `D1_MSRMT_RPT_CURR`: source `7,654,750`, snapshot `7,654,750` (match)
- `FT_GL_DISTRIBUTION_RPT_CURR`: source `27,708,613`, snapshot `27,708,613` (match)
- `D1_USAGE_RPT_CURR`: source `2,478,947`, snapshot `2,478,947` (match)
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: source raw `3,746,859`, source joined `3,746,859`, snapshot `3,746,859` (exact parity)

Scalar-detail duplicate-grain parity:

- source raw duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `146`
- source joined duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `146`
- snapshot duplicate `(D1_USAGE_ID, SEQ_NUM)` groups: `146`

QA disposition:

- `College Station` high-level QA now **passes** for baseline readiness.
- Keep 6-hour schedules un-applied until explicit rolling-window cutover approval (per rollout gating).

## Next Steps

1. All four fresh rollout clients now have baseline completion plus high-level QA pass documented.
2. Do not apply recurring 6-hour operational schedules until each client has
   passed the high-level QA and is explicitly approved for rolling cutover.
3. After approval, deploy rolling-window procedures, run one manual operational
   refresh, validate history retention, then schedule the 6-hour jobs.

## Cross-Client High-Level Data Quality Sweep (2026-05-04)

Scope: fresh rollout clients only (`citycorp`, `fonddulac`, `newark`, `collegestation`), excluding `ellensburg`.

Checks applied per client:

- row count and load freshness for active 7 snapshot tables
- required field-name presence for critical columns in each snapshot
- null-rate checks for critical key and driver columns

### Results Summary

| Client | Snapshot Rows/Freshness | Required Field Names | Critical Null Checks | Overall |
| --- | --- | --- | --- | --- |
| Citycorp | Pass | Pass | Pass | Pass |
| Fond Du Lac | Pass | Pass | Pass | Pass |
| Newark | Pass | Pass | Pass | Pass |
| College Station | Pass | Pass | Pass | Pass |

### Notes

- Required field-name checks returned no missing required columns in all four clients.
- Null checks for critical identifiers and time-driver fields returned `0` null rows across all four clients.
- `D1_USAGE_SCALAR_DTL_RPT_CURR` duplicate natural-key groups are present in some clients and were parity-validated against source during client QA; this is tracked behavior, not a field-quality failure.

## Assumptions

- These results are from the test client databases accessed through the current
  `.env` client aliases.
- The active rollout is limited to the 7 governed snapshots listed above.
- Scheduler timestamps are database/server timestamps as returned by Oracle.
- This status file documents rollout and QA state only; it does not replace
  final business-user validation or downstream Jaspersoft report signoff.
