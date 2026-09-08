# Ellensburg Active Snapshot Scheduler And QA - 2026-07-20

## Scope

Reference database: `ellensburg`

This pass treats the active operational set as:

- the original 7 governed reporting snapshots
- plus `CMS_SA_SNAPSHOT` as the scheduled domain-support snapshot used by the
  Standard Offering SA Snapshot / aged-balance Domains

The CMS views remain live domain-support views and are validated separately.

## Repository Changes Made

- Added `sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/05_schedule_cms_sa_snapshot_job.sql`.
- Updated `sql/performance/snapshots/deployment_steps/07_schedule_all_active_snapshots.sql` to include `CMS_SA_SNAPSHOT` as `[8/8]`.
- Updated `sql/performance/snapshots/apply_6hour_staggered_schedule_1am_base.sql` to include `JOB_REFRESH_CMS_SA_SNAPSHOT`.
- Updated `sql/performance/snapshots/impact/15_latest_active_snapshot_runs.sql` to report the CMS SA job.
- Updated `sql/performance/snapshots/deployment_steps/13_high_level_client_data_quality_checks.sql` to include CMS SA field and freshness checks.
- Updated rollout docs to describe the active 7 plus scheduled CMS SA support model.

## Database Change Applied

Created the Ellensburg scheduler job:

- job: `CISADM.JOB_REFRESH_CMS_SA_SNAPSHOT`
- action: `CISADM.REFRESH_CMS_SA_SNAPSHOT`
- cadence: `FREQ=DAILY;BYHOUR=4,10,16,22;BYMINUTE=30;BYSECOND=0`
- enabled: `TRUE`
- first next run observed: `2026-07-20 16:30:00.607774`

No refresh procedure logic was changed in the database.

## Fast Validation Results

### Object Status

All 8 tables and refresh procedures were `VALID` in `CISADM`:

- `FT_RPT_CURR` / `REFRESH_FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR` / `REFRESH_BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR` / `REFRESH_BSEG_SQ_USAGE_RPT_CURR`
- `D1_MSRMT_RPT_CURR` / `REFRESH_D1_MSRMT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR` / `REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_USAGE_RPT_CURR` / `REFRESH_D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR` / `REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR`
- `CMS_SA_SNAPSHOT` / `REFRESH_CMS_SA_SNAPSHOT`

### Scheduler Status

All 8 scheduler jobs are enabled and scheduled.

Latest observed original-7 runtimes:

| Table | Latest Status | Latest Runtime |
| --- | --- | ---: |
| `FT_RPT_CURR` | `SUCCEEDED` | `2.80` min |
| `BSEG_BILLED_USAGE_RPT_CURR` | `SUCCEEDED` | `2.62` min |
| `BSEG_SQ_USAGE_RPT_CURR` | `SUCCEEDED` | `1.72` min |
| `D1_MSRMT_RPT_CURR` | `SUCCEEDED` | `2.92` min |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `SUCCEEDED` | `1.18` min |
| `D1_USAGE_RPT_CURR` | `SUCCEEDED` | `9.08` min |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `SUCCEEDED` | `8.20` min |
| `CMS_SA_SNAPSHOT` | no run yet | first scheduled run pending |

Follow-up status check at database time `2026-07-20 15:03:59` showed
`FT_GL_DISTRIBUTION_RPT_CURR` had also run successfully at `15:00` in `1.23`
minutes. `CMS_SA_SNAPSHOT` still had no job run log yet; next scheduled run was
`2026-07-20 16:30:00.607774`.

### Row Counts And Field Presence

| Table | Rows | Latest/Freshness Note |
| --- | ---: | --- |
| `FT_RPT_CURR` | `4,856,754` | max load `2026-07-20 13:01:10.173001` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `2,215,381` | max load `2026-07-20 13:30:11.130413` |
| `BSEG_SQ_USAGE_RPT_CURR` | `3,747,320` | max load `2026-07-20 14:00:24.560552` |
| `D1_MSRMT_RPT_CURR` | `1,680,733` | max load `2026-07-20 14:30:15.921369` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `4,955,993` | max load `2026-07-20 09:00:16.317683` |
| `D1_USAGE_RPT_CURR` | `684,632` | max load `2026-07-20 09:39:03.854556` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `720,664` | max load `2026-07-20 10:07:54.013534` |
| `CMS_SA_SNAPSHOT` | `128,779` | snapshot date `2026-07-15` |

Required field presence check passed for all 8 tables:

- expected columns present: all
- missing columns: `0`

### CMS SA Specific Checks

- `CMS_SA_SNAPSHOT` row count: `128,779`
- snapshot type count: `1`
- snapshot date: `2026-07-15`
- `LDAY` duplicate `SA_ID` groups: `0`
- bucket identity gaps where `ARS_AMT1..5 != CUR_BAL`: `0`
- `SUM(CUR_BAL)`: `2,263,889.80`

## Schema Scope Clarification

Future snapshot rollout and QA work should validate through `CISADM` only.
`CISREAD` synonym checks are not part of the standard QA path.

## Static Procedure Source Review

No database procedure logic was changed. Static review of the repository refresh procedures found expected source families:

- `FT_RPT_CURR`: `CI_FT`, `CI_SA`, `CI_ACCT`, type-gated `CI_BSEG`, `CI_ADJ`, `CI_PAY_SEG`
- `BSEG_BILLED_USAGE_RPT_CURR`: `CI_BSEG`, `CI_BILL`, pre-aggregated `CI_BSEG_SQ`, `CI_BSEG_READ`, `CI_BSEG_CALC`
- `BSEG_SQ_USAGE_RPT_CURR`: `CI_BSEG_SQ`, `CI_BSEG`, `CI_BILL`
- `D1_MSRMT_RPT_CURR`: `D1_MSRMT`, `D1_MEASR_COMP`, `D1_INIT_MSRMT_DATA`, timestamp-constrained `D1_INSTALL_EVT`, `D1_SP`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `CI_FT_GL`, `CI_FT`, FT-family context joins
- `D1_USAGE_RPT_CURR`: `D1_USAGE`, `C1_USAGE`, `CI_BSEG`, `CI_SA`, account/premise context
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `D1_USAGE_SCALAR_DTL`, `D1_USAGE`, `C1_USAGE`, SA/account context
- `CMS_SA_SNAPSHOT`: frozen ARS `CI_FT`, `CI_SA`, `CI_ACCT`, main customer account-person context

Notable grain protections observed:

- BSEG billed aggregates child rows by `BSEG_ID` before joining.
- BSEG SQ groups determinant-level rows by `BSEG_ID`, `UOM_CD`, `TOU_CD`, and `SQI_CD`.
- D1 usage and scalar detail use ranked `C1_USAGE` bridge selection by `D1_USAGE_ID`.
- D1 measurement install-event enrichment is constrained by measurement timestamp and uses `NOT EXISTS` to choose the latest matching install event.
- CMS SA uses FIFO-style arrears aging and validates bucket sum back to `CUR_BAL`.

## Active 8 Integrity Audit - Ellensburg

Audit script:
`sql/performance/snapshots/qa/active8_snapshot_integrity_audit.sql`

Run command:

```bash
python3 scripts/local/run_client_oracle_sql.py --client ellensburg \
  --file sql/performance/snapshots/qa/active8_snapshot_integrity_audit.sql \
  --max-rows 100
```

Completed read-only against `CISADM` only.

### Grain Duplicate Check

| Snapshot | Tested grain | Duplicate keys |
| --- | --- | ---: |
| `FT_RPT_CURR` | `FT_ID` | `0` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `FT_ID + GL_SEQ_NBR` | `0` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `BSEG_ID` | `0` |
| `BSEG_SQ_USAGE_RPT_CURR` | `BSEG_ID + UOM + TOU + SQI` | `0` |
| `D1_MSRMT_RPT_CURR` | `MEASR_COMP_ID + MSRMT_DTTM` | `0` |
| `D1_USAGE_RPT_CURR` | `D1_USAGE_ID` | `0` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `D1_USAGE_ID + SEQ_NUM` | `48` |
| `CMS_SA_SNAPSHOT` | `SA_ID + C1_SNAPSHOT_DT + CM_SNAPSHOT_TYPE_FLG` | `0` |

Follow-up confirmed the same `48` duplicate `D1_USAGE_ID + SEQ_NUM` keys exist
in `CISADM.D1_USAGE_SCALAR_DTL`. They are not introduced by the refresh join.
Each duplicate pair had different measuring components and payloads, so the
row-level grain for scalar detail is wider than `D1_USAGE_ID + SEQ_NUM`.

### Source Row Coverage

All 8 snapshots had `0` missing source rows using the tested `CISADM` source
keys.

| Snapshot | Snapshot rows | Missing source rows |
| --- | ---: | ---: |
| `FT_RPT_CURR` | `4,856,754` | `0` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `4,955,993` | `0` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `2,215,381` | `0` |
| `BSEG_SQ_USAGE_RPT_CURR` | `3,747,320` | `0` |
| `D1_MSRMT_RPT_CURR` | `1,680,733` | `0` |
| `D1_USAGE_RPT_CURR` | `684,632` | `0` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `720,664` | `0` |
| `CMS_SA_SNAPSHOT` | `128,779` | `0` |

### Bill Cycle Null Gap Finding

Large cycle-code gaps remain where the `CISADM` source fallback has a value but
the snapshot stores a blank/null cycle.

| Snapshot | Checked rows | Snapshot null where source/fallback has value |
| --- | ---: | ---: |
| `BSEG_BILLED_USAGE_RPT_CURR.bill_bill_cyc_cd` | `2,215,381` | `1,194,442` |
| `BSEG_BILLED_USAGE_RPT_CURR.bseg_bill_cyc_cd` | `2,215,381` | `1,215,349` |
| `BSEG_SQ_USAGE_RPT_CURR.bill_bill_cyc_cd` | `3,747,320` | `875,925` |
| `BSEG_SQ_USAGE_RPT_CURR.bseg_bill_cyc_cd` | `3,747,320` | `947,315` |
| `FT_GL_DISTRIBUTION_RPT_CURR.bseg_bill_cyc_cd` | `4,955,993` | `2,567,961` |
| `FT_RPT_CURR.bill_cyc_cd` | `4,856,754` | `0` |
| `D1_USAGE_RPT_CURR.d1_bill_cyc_cd` | `684,632` | `0` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR.d1_bill_cyc_cd` | `720,664` | `0` |

Sample rows confirmed the issue pattern:

- snapshot cycle fields contained blank-padded values
- `CI_BILL.BILL_CYC_CD` and `CI_BSEG.BILL_CYC_CD` were blank
- `CI_ACCT.BILL_CYC_CD` contained the actual cycle value, such as `01` or `04`

Live Ellensburg procedure source also confirmed the deployed DB procedures do
not include the repository's documented `COALESCE(NULLIF(TRIM(...)), acct...)`
fallback logic yet. The live procedures still insert/join direct bill or bseg
cycle fields.

No procedure changes were applied in this pass.

### Procedure Update And Recovery - Later Same Day

After review approval, the following Ellensburg procedures were updated from
the repository versions so the live DB source matched the documented cycle
fallback logic:

- `CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR`
- `CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR`
- `CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`

Validation after compile:

- all 3 procedures were `VALID`
- `ALL_SOURCE` confirmed the `COALESCE(NULLIF(TRIM(...)), acct...)` fallback
  logic was present in Ellensburg

Manual rolling refreshes were run for the 3 updated procedures. The rolling
refreshes completed successfully and updated the active windows.

Important operational note:

- `BSEG_BILLED_USAGE_RPT_CURR` still had historical rows outside the rolling
  window that were loaded by the stale procedure.
- A client-side full-history procedure run hit the 15-minute call timeout.
- A DB-scheduler full-history run progressed through older sparse months but
  stalled at the 2019/2020 transition twice and was stopped.
- The table was recovered by restoring the rolling procedure and rerunning the
  active 12-month rolling refresh.

Final BSEG billed safety state after recovery:

| Check | Result |
| --- | ---: |
| `BSEG_BILLED_USAGE_RPT_CURR` rows | `237,727` |
| distinct `BSEG_ID` values | `237,727` |
| duplicate `BSEG_ID` keys | `0` |
| active-window bill-cycle source/fallback gaps | `0` |
| min `BILL_DT` | `2008-12-01` |
| max `BILL_DT` | `2028-02-01` |

The active reporting window is usable and the scheduled rolling procedure is
restored. Historical rows outside the active rolling window are not fully
restored to the previous full-history count and need a separate optimized
historical rebuild/backfill plan before relying on older BSEG billed history.

Full-history count gap after recovery:

| Expected full-history rows from `CI_BSEG` complete bills | Current snapshot rows | Missing historical rows |
| ---: | ---: | ---: |
| `2,215,381` | `237,727` | `1,977,654` |

Temporary scheduler job cleanup:

- `CISADM.JOB_ONCE_FULL_BSEG_BILLED_CYCLE_FIX` was stopped and dropped.

### Measure Parity

High-value totals matched source at the tested grain for the original 7
snapshot checks.

| Snapshot | Measure 1 delta | Measure 2 delta |
| --- | ---: | ---: |
| `FT_RPT_CURR` | `0` | `0` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `0` | `0` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `0` | `0` |
| `BSEG_SQ_USAGE_RPT_CURR` | `0` | `0` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `0` | `0` |
| `D1_MSRMT_RPT_CURR` | `0` | `0` |

`CMS_SA_SNAPSHOT` had a `700.60` delta against current live `CI_FT` source:

- snapshot `CUR_BAL`: `2,263,889.80`
- source current `CUR_BAL`: `2,263,189.20`
- delta: `700.60`
- snapshot `TOT_BAL`: `2,969,671.95`
- source current `TOT_BAL`: `2,968,971.35`
- delta: `700.60`

This is most likely freshness drift because the stored CMS SA snapshot date was
`2026-07-15`, while the parity query compares to current `CI_FT` as of
`2026-07-20`. Re-run this check after the first scheduled
`JOB_REFRESH_CMS_SA_SNAPSHOT` execution.

## Deferred QA

The full domain-support install gate was stopped because its FT parity scan was not fast enough for this pass. The high-level null-rate statement was also stopped after the first three high-level QA statements completed.

Recommended next QA, one table at a time:

- run targeted source-vs-snapshot parity only for a known date slice or one client-selected business segment
- run narrow null checks only where a report depends on a critical field
- after `JOB_REFRESH_CMS_SA_SNAPSHOT` runs once, confirm latest run status and runtime
- review whether to deploy the repository bill-cycle fallback procedure updates
  to Ellensburg for `BSEG_BILLED_USAGE_RPT_CURR`,
  `BSEG_SQ_USAGE_RPT_CURR`, and `FT_GL_DISTRIBUTION_RPT_CURR`
- build an optimized historical restore for `BSEG_BILLED_USAGE_RPT_CURR`
  instead of rerunning the current full-history procedure as-is
- review whether `D1_USAGE_SCALAR_DTL_RPT_CURR` reporting grain should be
  documented as including measuring component/service-point context where
  duplicate `D1_USAGE_ID + SEQ_NUM` source rows exist
