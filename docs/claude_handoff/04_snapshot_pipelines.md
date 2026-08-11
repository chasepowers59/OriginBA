# 04 — Snapshot pipelines & procedures

## Rule

Never modify C2M source tables for performance. Only snapshot copies (`*_RPT_CURR` / governed CMS objects).

## Active 7

1. `FT_RPT_CURR`
2. `BSEG_BILLED_USAGE_RPT_CURR`
3. `BSEG_SQ_USAGE_RPT_CURR`
4. `D1_MSRMT_RPT_CURR`
5. `FT_GL_DISTRIBUTION_RPT_CURR`
6. `D1_USAGE_RPT_CURR`
7. `D1_USAGE_SCALAR_DTL_RPT_CURR`

Plus domain-support: `CMS_SA_SNAPSHOT` (debt Domains).

## Canonical deploy folder

`sql/performance/snapshots/deployment_steps/`

### Sequence (summary)

1. `01_create_all_active_snapshot_tables.sql`
2. `01b_create_all_domain_support_objects.sql`
3. `02_deploy_all_initial_full_history_procedures.sql` (baseline `02a` procs)
4. `02b_deploy_domain_support_procedures.sql`
5. Baseline load: `03_*` (manual or scheduled once-jobs)
6. Validate: `04_*` gates
7. Rolling: `05_deploy_all_rolling_window_updates.sql`
8. Schedule: `07_schedule_all_active_snapshots.sql`

Full README: `sql/performance/snapshots/deployment_steps/README.md`

## Baseline vs rolling

- **Baseline (`02a`)**: seed history (client-specific window, e.g. Newark 24 months)
- **Rolling (`02`)**: refresh recent window only; do not truncate full table
- Scheduler: prefer **`RUN_JOB` only** on once-jobs — do **not** `ENABLE` + `RUN_JOB` (double-fire bug)

## Newark TEST cutover (2yr / 3mo rolling)

See `sql/performance/snapshots/deployment_steps/clients/newark/README.md`

```bash
# Deploy 24-month baseline procs
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql

# Parallel baselines (RUN_JOB only)
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/clients/newark/03_run_all_2yr_baselines_parallel_now.sql

# After success: 3mo rolling / 24mo retain procs
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/clients/newark/02_deploy_3mo_rolling_24mo_retain_procedures.sql
```

AFTER QA helper: `scripts/local/newark_after_qa_2yr.py`  
Logs: `deploy/snapshot_rollout_logs/newark/`

## Client helpers

| Path | Purpose |
|------|---------|
| `deployment_steps/clients/run_all_baselines_parallel_now.sql` | Parallel baselines |
| `deployment_steps/clients/run_all_baselines_3stream_now.sql` | 3-stream variant |
| `deployment_steps/clients/post_load_snapshot_indexes_limited_priv.sql` | Indexes after load |
| `deployment_steps/clients/post_create_grants_resilient.sql` | Grants |
| `deployment_steps/13_high_level_client_data_quality_checks.sql` | DQ checks |

## Docs

- `sql/performance/snapshots/docs/snapshot_client_reporting_guide.md`
- `docs/smartcity_client_snapshot_rollout_runbook.md`
- `docs/smartcity_client_snapshot_rollout_status_2026-04-30.md`
