---
name: originba-snapshot-rollout-qa
description: Deploy and QA Oracle snapshot baselines and rolling refreshes on SmartCity client TEST environments.
---

# OriginBA Snapshot Rollout QA

## When to use

- 2-year baseline cutover, rolling refresh deployment
- BEFORE/AFTER fingerprint and source parity
- Client snapshot rollout status updates

## Required references

- `sql/performance/snapshots/deployment_steps/clients/<client>/README.md`
- `sql/performance/snapshots/docs/snapshot_client_reporting_guide.md`
- `docs/smartcity_client_snapshot_rollout_status_2026-04-30.md`
- `scripts/local/run_client_oracle_sql.py`
- `scripts/local/newark_after_qa_2yr.py` (Newark pattern)

## Steps

1. Never modify C2M source tables; only `*_RPT_CURR` and snapshot copies.
2. BEFORE: capture fingerprints and source parity for the retention window.
3. Deploy procedures from `sql/performance/snapshots/deployment_steps/`.
4. Submit baseline jobs with `RUN_JOB` only (do not combine `ENABLE` + `RUN_JOB` on once jobs).
5. AFTER: retention check + parity on known slices; log under `deploy/snapshot_rollout_logs/<client>/`.
6. Document EXACT vs NEAR parity gaps with root cause (logic vs data window vs environment).
7. Hold rolling schedule on TEST until explicitly approved.

## Output contract

- Read-only validation unless user explicitly requests proc deployment
- Log paths and run metadata documented
- PASS/FAIL summary per snapshot table
