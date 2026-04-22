# Active Snapshot Deployment Steps

Use this folder as the centralized deployment reference for the active 7 governed snapshots.

Run these scripts in `SQL Developer` or `SQLcl` as **script execution** (`F5` / `@file.sql`), not as single-statement execution, because they rely on `@@` includes and PL/SQL blocks.

## Active 7 snapshots
- `FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

## Deployment sequence
1. `01_create_all_active_snapshot_tables.sql`
2. `02_deploy_all_initial_full_history_procedures.sql`
3. `03_run_all_initial_full_history_refreshes.sql`
4. `04_validate_all_active_snapshots.sql`
5. `05_deploy_all_rolling_window_updates.sql`
6. `06_run_all_operational_refreshes.sql`
7. `04_validate_all_active_snapshots.sql` again
8. `07_schedule_all_active_snapshots.sql`
9. `08_capture_latest_active_snapshot_runs.sql`

## Optional BSEG rolling-window candidate flow

Do not use this flow until the BSEG diagnostics support it.

1. `09_bseg_rolling_window_preflight.sql`
2. `10_deploy_bseg_candidate_rolling_updates.sql`
3. `11_run_bseg_candidate_refreshes.sql`
4. `12_validate_bseg_candidate_rolling_updates.sql`

## Baseline vs operational procedure model

This deployment set intentionally separates:
- **initial baseline deployment**
  - full-history procedures for snapshots that need a one-time historical seed
- **operational deployment**
  - rolling-window procedures for approved snapshots
  - unchanged full-refresh procedures for snapshots that do not have an approved rolling-window model

### Rolling-window approved snapshots
- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

### Full-refresh only snapshots
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`

Candidate rolling-window files now exist for both BSEG snapshots, but they are still pre-validation only.

## Validation guidance

`04_validate_all_active_snapshots.sql` is intentionally reusable:
- run it after the initial full-history baseline load
- run it again after operational procedure cutover and manual refresh

The script calls the package-level validation that is currently considered the right balance of speed and coverage for each snapshot.

## Scheduling guidance

`07_schedule_all_active_snapshots.sql`:
- creates the scheduler jobs from the package-level job scripts
- then applies the current approved staggered 6-hour cadence from:
  - [apply_6hour_staggered_schedule_1am_base.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/apply_6hour_staggered_schedule_1am_base.sql)

## Manifest

For the exact source files each wrapper script targets, use:
- [00_active_snapshot_deployment_manifest.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/deployment_steps/00_active_snapshot_deployment_manifest.md)
