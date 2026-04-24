# Active 5 Snapshot Procedure Review

Date: `2026-04-24`

## Purpose

This document records the readiness review for the five active scheduled
snapshot procedures that remained after the BSEG rolling-window cutovers:

- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

The goal was to confirm that each active procedure is:

- preserved with a full-history baseline option
- operating with the intended rolling-window or approved refresh strategy
- valid and actively scheduled in the database
- backed by QA evidence strong enough to keep it in the active 7-snapshot set

## Scope

This review covered the current repo assets plus read-only validation against
the connected test database.

It did not modify any database procedures.

## Validation Approach

For each of the five procedures, the review checked:

1. the active procedure file in the repo
2. the preserved full-history baseline procedure
3. the README and local documentation
4. active scheduler/runtime status in the database
5. the highest-signal validation pack available for current refresh behavior

## Database Status

All five procedures are currently `VALID` in the database.

Latest observed scheduler runs on `2026-04-24`:

| Snapshot | Job | Latest Status | Run Minutes |
|---|---|---|---:|
| `FT_RPT_CURR` | `JOB_REFRESH_FT_RPT_CURR` | `SUCCEEDED` | `3.22` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR` | `SUCCEEDED` | `11.63` |
| `D1_MSRMT_RPT_CURR` | `JOB_REFRESH_D1_MSRMT_RPT_CURR` | `SUCCEEDED` | `4.10` |
| `D1_USAGE_RPT_CURR` | `JOB_REFRESH_D1_USAGE_RPT_CURR` | `SUCCEEDED` | `9.52` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR` | `SUCCEEDED` | `7.52` |

## Findings

### 1. `FT_RPT_CURR` is ready

Evidence:

- preserved baseline procedure exists:
  [02a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_rpt_curr/02a_full_history_refresh_procedure.sql)
- active procedure uses rolling 12-month maintenance:
  [02_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_rpt_curr/02_refresh_snapshot_procedure.sql)
- fast validation passed:
  - whole-table row count exact: `4,856,139`
  - current total `CUR_AMT` exact: `3,009,000.30`
  - current total `TOT_AMT` exact: `3,682,465.90`
  - rolling 12-month monthly parity exact
  - duplicate `FT_ID` rows: none

Conclusion:

- technically ready
- no procedure change needed

Note:

- the README had stale wording that still described the load as full
  `TRUNCATE` reload; that documentation was corrected in this review

### 2. `FT_GL_DISTRIBUTION_RPT_CURR` is ready

Evidence:

- preserved baseline procedure exists:
  [02a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_gl_distribution/02a_full_history_refresh_procedure.sql)
- active procedure initially used rolling 12-month maintenance and was then
  narrowed to rolling 6-month maintenance on `2026-04-24`:
  [02_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_gl_distribution/02_refresh_snapshot_procedure.sql)
- fast validation passed:
  - whole-table row count exact: `4,954,606`
  - total `GL_AMOUNT` exact: `0`
  - total `STATISTIC_AMOUNT` exact: `475,046,395.33187`
  - rolling 12-month monthly parity exact even after the 6-month cutover
  - duplicate `(FT_ID, GL_SEQ_NBR)` rows: none
- manual 6-month cutover refresh completed in `5.89` minutes versus the prior
  latest scheduler sample of `11.63` minutes

Conclusion:

- technically ready
- no procedure change needed

### 3. `D1_MSRMT_RPT_CURR` is ready

Evidence:

- preserved baseline procedure exists:
  [01a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_msrmt/01a_full_history_refresh_procedure.sql)
- active procedure uses rolling 12-month maintenance:
  [01_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_msrmt/01_refresh_snapshot_procedure.sql)
- fast validation passed:
  - whole-table row count exact: `1,680,216`
  - total `MSRMT_VAL` exact: `43,505,816,441.986`
  - total `READING_VAL` exact: `119,822,953,344.0725`
  - rolling 12-month monthly parity exact
  - duplicate `(MEASR_COMP_ID, MSRMT_DTTM)` rows: none

Conclusion:

- technically ready
- no procedure change needed

### 4. `D1_USAGE_RPT_CURR` is ready

Evidence:

- preserved baseline procedure exists:
  [02a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_usage/02a_full_history_refresh_procedure.sql)
- active procedure uses rolling 12-month maintenance in 3-month batches:
  [02_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_usage/02_refresh_snapshot_procedure.sql)
- validation passed:
  - whole-table row count stable: `684,214`
  - rolling 12-month monthly parity exact
  - older-than-window history retained
  - duplicate `D1_USAGE_ID` rows: none
  - bridge/account coverage remains populated for the in-window slice

Conclusion:

- technically ready
- no procedure change needed

### 5. `D1_USAGE_SCALAR_DTL_RPT_CURR` is operationally usable but not fully verified at the stated natural key

Evidence:

- preserved baseline procedure exists:
  [02a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/02a_full_history_refresh_procedure.sql)
- active procedure uses rolling 12-month maintenance in 3-month batches:
  [02_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/02_refresh_snapshot_procedure.sql)
- additive parity passed:
  - rolling 12-month monthly row parity exact
  - rolling 12-month `QUANTITY` parity exact
  - rolling 12-month `FINAL_QUANTITY` parity exact
  - older-than-window history retained
- duplicate-key check failed for the stated natural key `(D1_USAGE_ID, SEQ_NUM)`

Important clarification:

- the duplicate-key issue was not introduced by the snapshot procedure
- the source table `CISADM.D1_USAGE_SCALAR_DTL` already has the same duplicate
  count at that key shape: `48`
- the snapshot currently mirrors that source condition exactly

Conclusion:

- the procedure is behaving consistently with source
- the current documented natural key is not defensible as a guaranteed unique
  key in this environment
- this snapshot should not be described as fully verified until one of these is
  resolved:
  1. document that source can legitimately contain duplicate
     `(D1_USAGE_ID, SEQ_NUM)` rows and stop calling that pair a strict natural
     key
  2. identify a stronger unique determinant for the snapshot grain
  3. introduce an approved de-duplication rule, but only after source/business
     review

## Overall Readiness Decision

### Ready now

- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `D1_USAGE_RPT_CURR`

### Needs follow-up before it can be called fully verified

- `D1_USAGE_SCALAR_DTL_RPT_CURR`

Reason:

- source-consistent duplicate natural-key rows

## Recommended Next Actions

1. Keep the four clean procedures in the active approved set with no DB changes.
2. Correct repo wording anywhere `FT_RPT_CURR` is still described as a full
   reload.
3. Treat `D1_USAGE_SCALAR_DTL_RPT_CURR` as a targeted follow-up:
   - inspect the 48 duplicate source key cases
   - decide whether the grain definition or de-duplication rule needs to change
   - do not change the procedure until the source-key interpretation is settled

## Why No Procedure Change Was Made

The user requirement was:

- do not change procedures unless the right approach is confirmed
- always do QA after any change

That standard means `D1_USAGE_SCALAR_DTL_RPT_CURR` should stay unchanged for now.
The current evidence points to a source/grain-definition issue, not a safe
procedure fix that should be applied immediately.
