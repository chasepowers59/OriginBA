# College Station TEST snapshot cutover (2 years / 3-month rolling)

## Policy
- Snapshot retention: trailing **24 months**
- Operational rolling refresh: trailing **3 months** (plus purge older than 24 months)
- Baseline/historical seed: trailing **24 months** (no unbounded full history)
- Active 8 = active 7 `*_RPT_CURR` + `CMS_SA_SNAPSHOT`

## Preferred cutover (rebuild on 25.4 TEST)
```bash
# 0) Create tables/views/procs + grants + kick 24mo baselines (limited-priv path)
SKIP_BASELINE_KICK=1 bash scripts/local/install_limited_priv_snapshot_client.sh collegestation

# 1) Deploy/confirm 24-month baseline (02a) procedures
python3 scripts/local/run_client_oracle_sql.py --client collegestation \
  --file sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql

# 2) Submit all 7 baselines in parallel (RUN_JOB only)
python3 scripts/local/run_client_oracle_sql.py --client collegestation \
  --file sql/performance/snapshots/deployment_steps/clients/collegestation/03_run_all_2yr_baselines_parallel_now.sql

# 3) After all JOB_BASELINE_*_ONCE succeed:
#    post-load indexes, 3mo rolling procs, schedule, CMS SA refresh, QA
python3 scripts/local/run_client_oracle_sql.py --client collegestation \
  --file sql/performance/snapshots/deployment_steps/clients/post_load_snapshot_indexes_limited_priv.sql

python3 scripts/local/run_client_oracle_sql.py --client collegestation \
  --file sql/performance/snapshots/deployment_steps/clients/collegestation/02_deploy_3mo_rolling_24mo_retain_procedures.sql

python3 scripts/local/run_snapshot_rollout_step.py \
  --step schedule-operational --clients collegestation

python3 scripts/local/run_snapshot_rollout_step.py \
  --step domain-support-deploy-and-validate --clients collegestation

python3 scripts/local/run_snapshot_rollout_step.py \
  --step baseline-and-validate --clients collegestation

DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/collegestation_after_qa_2yr.py
```

Logs: `deploy/snapshot_rollout_logs/collegestation/`
