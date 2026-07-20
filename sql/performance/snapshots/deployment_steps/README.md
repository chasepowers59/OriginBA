# Active Snapshot Deployment Steps

Use this folder as the centralized deployment reference for the active 7 governed snapshots.

Client reporting guide (use cases, example reports, population scope): [../docs/snapshot_client_reporting_guide.md](../docs/snapshot_client_reporting_guide.md)

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
2. `01b_create_all_domain_support_objects.sql` — CMS views + `CMS_SA_SNAPSHOT`
3. `02_deploy_all_initial_full_history_procedures.sql`
4. `02b_deploy_domain_support_procedures.sql` — `REFRESH_CMS_SA_SNAPSHOT`
5. Choose one baseline load option:
   - `03_run_all_initial_full_history_refreshes.sql` for a manual foreground run
   - `03a_schedule_all_initial_full_history_refreshes.sql` for unattended one-time baseline jobs
6. `03e_run_domain_support_refreshes.sql` — refresh CMS SA snapshot (can run in parallel with baseline)
7. If using scheduled baseline jobs, run `03b_capture_initial_full_history_job_status.sql` later
8. `04_validate_all_active_snapshots.sql`
9. `04c_validate_all_domain_support_objects.sql`
10. `04b_snapshot_install_validation_gate.sql`
11. `04d_domain_support_install_validation_gate.sql`
12. `05_deploy_all_rolling_window_updates.sql`
13. `06_run_all_operational_refreshes.sql` (includes CMS SA refresh)
14. `04_validate_all_active_snapshots.sql` again
15. `04c_validate_all_domain_support_objects.sql` again
16. `04b_snapshot_install_validation_gate.sql` and `04d_domain_support_install_validation_gate.sql` again
17. `07_schedule_all_active_snapshots.sql`
18. `08_capture_latest_active_snapshot_runs.sql`

## BSEG promotion flow

The BSEG-specific promotion flow was the validation path used to approve the
 billing snapshots for rolling-window maintenance on `2026-04-24`.

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

For the BSEG snapshots, this means:
- first deployment into a new database:
  - use `02a_full_history_refresh_procedure.sql`
- after the baseline history exists:
  - switch to `02_refresh_snapshot_procedure.sql`
- the rolling procedure deletes and rebuilds only the most recent `12` months;
  it does not truncate the full table

### Rolling-window approved snapshots
- `FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

## Validation guidance

`04_validate_all_active_snapshots.sql` is intentionally reusable:
- run it after the initial full-history baseline load
- run it again after operational procedure cutover and manual refresh

The script calls the package-level validation that is currently considered the right balance of speed and coverage for each snapshot.

For the two BSEG snapshots, the fast validators became the operational QA gate
 during the `2026-04-24` rolling-window cutover because they verify:

- preserved whole-table row counts
- rolling `12-month` monthly parity
- additive total parity
- duplicate-key safety

## Unattended first-load option

`03a_schedule_all_initial_full_history_refreshes.sql` creates one-time baseline
jobs staggered every 15 minutes, starting at the script run time.
Use this when loading client databases so the first full-history loads can run
without keeping a local terminal session open.

After the scheduled start window has elapsed, use:

- `03b_capture_initial_full_history_job_status.sql`
- `baseline-and-validate` compound step (recommended)

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step baseline-and-validate --clients newark
```

This chains baseline status capture, baseline job gate, full validation, and install
sanity gate. It exits non-zero and writes a failure marker under
`deploy/snapshot_rollout_logs/` when anything fails.

Do not deploy the rolling-window procedures or recurring 6-hour jobs until the
baseline job gate and validation output are acceptable.

## Install validation compound steps

Use these for first-time client install QA. They run the full validation pack and
fail fast when baseline jobs or snapshot sanity checks do not pass.

| Step | When to use |
| --- | --- |
| `baseline-and-validate` | After baseline one-time jobs finish |
| `domain-support-deploy-and-validate` | Create/deploy/refresh CMS layer + gate |
| `operational-and-validate` | After manual operational refresh during cutover |
| `cutover-and-validate` | Deploy rolling procs, run operational refresh, validate |

Examples:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step baseline-and-validate --clients newark
python3 scripts/local/run_snapshot_rollout_step.py --step domain-support-deploy-and-validate --clients newark
python3 scripts/local/run_snapshot_rollout_step.py --step cutover-and-validate --clients newark
```

Gate scripts:

- `03d_baseline_jobs_ready_gate.sql` — fails when any baseline one-time job is not `SUCCEEDED`
- `04b_snapshot_install_validation_gate.sql` — fails on empty tables or duplicate grain keys (active 7)
- `04d_domain_support_install_validation_gate.sql` — fails on invalid CMS views, bucket gaps, or FT parity on `CMS_SA_SNAPSHOT`

Logs for compound steps:

- `deploy/snapshot_rollout_logs/<client>/<compound_step>/`

## Scheduling guidance

`07_schedule_all_active_snapshots.sql`:
- creates the scheduler jobs from the package-level job scripts
- then applies the current approved staggered 6-hour cadence from:
  - [apply_6hour_staggered_schedule_1am_base.sql](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/sql/performance/snapshots/apply_6hour_staggered_schedule_1am_base.sql)

## Consolidation snapshots (12 tables)

Workstream consolidation phase uses scripts **21–28** with the same baseline → rolling → schedule model (6-month rolling window).

Runbook: [smartcity_consolidation_snapshot_rollout_runbook.md](../../../docs/smartcity_consolidation_snapshot_rollout_runbook.md)

| Step | Script |
| --- | --- |
| Create tables | `21_create_all_consolidation_snapshot_tables.sql` |
| Deploy baseline (`02a`) | `22_deploy_all_consolidation_baseline_procedures.sql` |
| Schedule baseline jobs | `23a_schedule_all_consolidation_baseline_refreshes.sql` |
| Baseline status / gate | `23b_…`, `23d_consolidation_baseline_jobs_ready_gate.sql` |
| Validate | `24_validate_all_consolidation_snapshots.sql` |
| Deploy rolling (`02`) | `25_deploy_all_consolidation_rolling_procedures.sql` |
| Run operational once | `26_run_all_consolidation_operational_refreshes.sql` |
| Schedule 6-hour jobs | `27_schedule_all_consolidation_snapshots.sql` |

Batch wrapper examples:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step consolidation-create-tables --clients newark
python3 scripts/local/run_snapshot_rollout_step.py --step consolidation-baseline-and-validate --clients newark
python3 scripts/local/run_snapshot_rollout_step.py --step consolidation-cutover-and-validate --clients newark
python3 scripts/local/run_snapshot_rollout_step.py --step consolidation-schedule-operational --clients newark
```

Manifest: [00_consolidation_snapshot_deployment_manifest.md](00_consolidation_snapshot_deployment_manifest.md)

## Manifest

For the exact source files each wrapper script targets, use:
- Active 7: [00_active_snapshot_deployment_manifest.md](00_active_snapshot_deployment_manifest.md)
- Domain support (CMS views + `CMS_SA_SNAPSHOT`): [00_domain_support_deployment_manifest.md](00_domain_support_deployment_manifest.md)
- Consolidation 12: [00_consolidation_snapshot_deployment_manifest.md](00_consolidation_snapshot_deployment_manifest.md)
