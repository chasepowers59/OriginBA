# Newark TEST snapshot retention cutover (2 years / 3-month rolling)

## Policy
- Snapshot retention: trailing **24 months**
- Operational rolling refresh: trailing **3 months** (plus purge older than 24 months)
- Baseline/historical seed: trailing **24 months** (no unbounded full history)

## One-time trim (Newark TEST)
```bash
# BEFORE fingerprint + source parity
DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/newark_trim_snapshots_2yr.py before

# Purge rows older than 24 months
DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/newark_trim_snapshots_2yr.py purge

# Gather stats
DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/newark_trim_snapshots_2yr.py stats

# AFTER fingerprint + source parity (keep-window must match BEFORE)
DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/newark_trim_snapshots_2yr.py after
```

Logs: `deploy/snapshot_rollout_logs/newark/trim_2yr_20260805/`

## Preferred cutover (truncate + 2yr baseline on DB)
```bash
# 1) Deploy 24-month baseline (02a) procedures
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql

# 2) Pause rolling refreshes and submit all 7 baselines in parallel
#    (script uses RUN_JOB only — does not ENABLE — so jobs cannot double-fire)
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/clients/newark/03_run_all_2yr_baselines_parallel_now.sql

# 3) After all JOB_BASELINE_*_ONCE succeed, deploy 3-month rolling procs
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/clients/newark/02_deploy_3mo_rolling_24mo_retain_procedures.sql
```

## Deploy updated rolling procedures only
```bash
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/performance/snapshots/deployment_steps/clients/newark/02_deploy_3mo_rolling_24mo_retain_procedures.sql
```
