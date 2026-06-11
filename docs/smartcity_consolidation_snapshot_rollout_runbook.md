# Consolidation Snapshot Client Rollout Runbook

## Scope

This runbook covers the **12 workstream consolidation snapshots** for SmartCity client
test databases. It follows the same pattern as the active-7 rollout:

1. **Baseline:** deploy `02a` full-history procedures, load all history once.
2. **Cutover:** deploy `02` six-month rolling procedures, run one manual refresh.
3. **Schedule:** create recurring 6-hour DBMS_SCHEDULER jobs.

### Tables

| Workstream | Table |
|---|---|
| Customer Operations | `ACCT_CUSTOMER_RPT_CURR`, `CASE_PREM_CONTACT_RPT_CURR` |
| New Services | `NEW_SERVICE_PIPELINE_RPT_CURR` |
| Field Operations | `FIELD_ACTIVITY_RPT_CURR`, `CREW_OPS_RPT_CURR` |
| Meter Operations | `DEVICE_SP_RPT_CURR` |
| Cashiering | `PAY_EVENT_RPT_CURR` |
| Finance | `BILLABLE_CHARGE_RPT_CURR` |
| Debt Management | `SA_AGED_BAL_RPT_CURR`, `WO_PROC_RPT_CURR` |
| Common | `OPS_EXCEPTION_RPT_CURR`, `WORKFLOW_QUEUE_RPT_CURR` |

Manifest and source paths: [00_consolidation_snapshot_deployment_manifest.md](../sql/performance/snapshots/deployment_steps/00_consolidation_snapshot_deployment_manifest.md)

## Prerequisites

- Target client already has the **active 7 snapshots** baseline-complete (recommended).
- VPN / DB access configured in local `.env` for the client alias.
- Demo QA passed: [physical_table_qa_status_2026-05-20.md](../deploy/snapshot_rollout_logs/demo/consolidation/physical_table_qa_status_2026-05-20.md)

Supported client aliases: `newark`, `fonddulac`, `collegestation`, `citycorp`, `ellensburg`, `demo`

## Deployment sequence

Use `python3 scripts/local/run_client_oracle_sql.py --client <client> --file <script>` or the
batch wrapper `run_snapshot_rollout_step.py` with `consolidation-*` steps.

| Step | Script | Purpose |
|---|---|---|
| 1 | `21_create_all_consolidation_snapshot_tables.sql` | DDL |
| 2 | `22_deploy_all_consolidation_baseline_procedures.sql` | Deploy `02a` |
| 3a | `23a_schedule_all_consolidation_baseline_refreshes.sql` | Unattended baseline jobs (recommended) |
| 3 | `23_run_all_consolidation_baseline_refreshes.sql` | Manual foreground baseline (alternative) |
| 4 | `23b_capture_consolidation_baseline_job_status.sql` | Job status + row counts |
| 5 | `23d_consolidation_baseline_jobs_ready_gate.sql` | Fail if any baseline job ≠ SUCCEEDED |
| 6 | `24_validate_all_consolidation_snapshots.sql` | Package validation per snapshot |
| 7 | `24b_consolidation_install_validation_gate.sql` | Empty table / duplicate grain gate |
| 8 | `25_deploy_all_consolidation_rolling_procedures.sql` | Deploy `02` (6-month rolling) |
| 9 | `26_run_all_consolidation_operational_refreshes.sql` | One manual operational refresh |
| 10 | `24_validate_all_consolidation_snapshots.sql` | Re-validate after cutover |
| 11 | `24b_consolidation_install_validation_gate.sql` | Re-run install gate |
| 12 | `27_schedule_all_consolidation_snapshots.sql` | Recurring 6-hour jobs |
| 13 | `28_capture_latest_consolidation_snapshot_runs.sql` | Capture scheduler runs |

### Batch commands (recommended)

```bash
# Phase A — baseline
python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-create-tables --clients newark

python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-deploy-baseline-procs --clients newark

python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-schedule-baseline --clients newark

# Wait ~3 hours for staggered baseline jobs (12 × 15 min), then:
python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-baseline-and-validate --clients newark

# Optional supplemental population QA
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql

# Phase B — rolling cutover (only after baseline gate passes)
python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-cutover-and-validate --clients newark

# Phase C — schedules (only after cutover gate passes)
python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-schedule-operational --clients newark

python3 scripts/local/run_snapshot_rollout_step.py \
  --step consolidation-latest-runs --clients newark
```

### Compound steps

| Step | Chains |
|---|---|
| `consolidation-baseline-and-validate` | baseline-status → baseline-jobs-gate → validate → install-validation-gate |
| `consolidation-operational-and-validate` | run-operational → validate → install-validation-gate |
| `consolidation-cutover-and-validate` | deploy-rolling-procs → run-operational → validate → install-validation-gate |

Logs: `deploy/snapshot_rollout_logs/<client>/consolidation/<step>/`

## Baseline job stagger

One-time jobs start immediately and stagger every **15 minutes** (light → heavy):

| Offset | Snapshot |
|---:|---|
| +0 min | `ACCT_CUSTOMER_RPT_CURR` |
| +15 | `CASE_PREM_CONTACT_RPT_CURR` |
| +30 | `CREW_OPS_RPT_CURR` |
| +45 | `WO_PROC_RPT_CURR` |
| +60 | `SA_AGED_BAL_RPT_CURR` |
| +75 | `NEW_SERVICE_PIPELINE_RPT_CURR` |
| +90 | `FIELD_ACTIVITY_RPT_CURR` |
| +105 | `DEVICE_SP_RPT_CURR` |
| +120 | `PAY_EVENT_RPT_CURR` |
| +135 | `BILLABLE_CHARGE_RPT_CURR` |
| +150 | `WORKFLOW_QUEUE_RPT_CURR` |
| +165 | `OPS_EXCEPTION_RPT_CURR` |

Allow **~3 hours** after scheduling before running the baseline gate.

## Operational schedule

Recurring jobs use a **6-hour cadence** with a **04:00 GMT base**, staggered across
hours 4–9 so they do not overlap the active-7 jobs (01:00–03:30 GMT base).

Stagger definition: [apply_6hour_staggered_schedule_consolidation_4am_base.sql](../sql/performance/snapshots/apply_6hour_staggered_schedule_consolidation_4am_base.sql)

Do **not** create recurring consolidation schedules until:

- all 12 baseline one-time jobs show `SUCCEEDED`
- `24_validate_all_consolidation_snapshots.sql` passes
- `24b_consolidation_install_validation_gate.sql` returns zero rows
- one manual operational refresh passes the same validation gates

## QA gates

### Baseline pass criteria

- All 12 `JOB_BASELINE_*_RPT_CURR_ONCE` jobs `SUCCEEDED`
- No empty snapshot tables (install gate)
- No duplicate natural-key groups (install gate)
- Package `04_validation_queries.sql` outputs acceptable per snapshot

### Cutover pass criteria

- Operational refresh completes without ORA errors
- Row counts remain populated; history outside 6-month scope retained where applicable
- Re-validation passes

### Supplemental (first client only)

```bash
bash scripts/local/run_consolidation_snapshot_demo_qa.sh <client>
python3 scripts/local/audit_consolidation_snapshot_physical_sources.py
```

## Rollout status tracking

Create per-client status under:

`deploy/snapshot_rollout_logs/<client>/consolidation/rollout_status.md`

Record: deploy dates, baseline job completion times, row counts, cutover approval, schedule creation.

## Relationship to active-7 runbook

- [smartcity_client_snapshot_rollout_runbook.md](smartcity_client_snapshot_rollout_runbook.md) — original 7 snapshots
- This runbook — consolidation phase 2 (12 additional tables)
- Jaspersoft Domains should not repoint until the target client passes consolidation baseline + cutover validation

## Jaspersoft Domain import (after client validation)

Import-ready Domain schema XML is in `domains/exports/manual_imports/` (colocated copies in each snapshot workspace). Regenerate from DDL with:

```bash
python3 scripts/build_consolidation_domain_xml.py
```

| Snapshot | Domain XML |
|---|---|
| `ACCT_CUSTOMER_RPT_CURR` | `ACCT_CUSTOMER_RPT_CURR_End_User_Friendly.xml` |
| `CASE_PREM_CONTACT_RPT_CURR` | `CASE_PREM_CONTACT_RPT_CURR_End_User_Friendly.xml` |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | `NEW_SERVICE_PIPELINE_RPT_CURR_End_User_Friendly.xml` |
| `FIELD_ACTIVITY_RPT_CURR` | `FIELD_ACTIVITY_RPT_CURR_End_User_Friendly.xml` |
| `CREW_OPS_RPT_CURR` | `CREW_OPS_RPT_CURR_End_User_Friendly.xml` |
| `DEVICE_SP_RPT_CURR` | `DEVICE_SP_RPT_CURR_End_User_Friendly.xml` |
| `PAY_EVENT_RPT_CURR` | `PAY_EVENT_RPT_CURR_End_User_Friendly.xml` |
| `BILLABLE_CHARGE_RPT_CURR` | `BILLABLE_CHARGE_RPT_CURR_End_User_Friendly.xml` |
| `SA_AGED_BAL_RPT_CURR` | `SA_AGED_BAL_RPT_CURR_End_User_Friendly.xml` |
| `WO_PROC_RPT_CURR` | `WO_PROC_RPT_CURR_End_User_Friendly.xml` |
| `OPS_EXCEPTION_RPT_CURR` | `OPS_EXCEPTION_RPT_CURR_End_User_Friendly.xml` |
| `WORKFLOW_QUEUE_RPT_CURR` | `WORKFLOW_QUEUE_RPT_CURR_End_User_Friendly.xml` |

Each domain is single-table, datasource alias `Origin_DEV_DS`, schema alias `CISADM`, with business item groups for Ad Hoc. Do not import to JRS until the target client snapshot tables pass baseline validation.

Inventory: [snapshot_xml_inventory.md](../sql/performance/snapshots/docs/snapshot_xml_inventory.md)

## Assumptions

- Schema owner is `CISADM` in each test database.
- `02a` is used only for initial seed; `02` replaces it before scheduling.
- Six-month rolling scope matches consolidation snapshot design (filters in `02`, not `02a`).
- CMS identifier views remain in use for `DEVICE_SP_RPT_CURR` enrichment.

## TEMP / runtime notes

- `OPS_EXCEPTION_RPT_CURR` and `WORKFLOW_QUEUE_RPT_CURR` are the longest baseline loads; they run last by design.
- If a baseline job fails with `ORA-01652`, resolve TEMP capacity before retrying; the procedure truncates and rebuilds from scratch on rerun.
- Do not stack consolidation baseline jobs on top of active-7 baseline jobs on the same database.
