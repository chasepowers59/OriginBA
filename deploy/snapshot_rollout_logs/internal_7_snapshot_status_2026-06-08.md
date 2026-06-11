# Internal 7-Snapshot Rollout Status — 2026-06-08

## Databases (internal — demo credentials)

| Client key | Environment | DSN |
| --- | --- | --- |
| `int_train` | Int Train | `smartcity-db-demo.originsmartops.com:1521/ptrndb_demo.demoprivatesn2.origindemovcn.oraclevcn.com` |
| `int_dev` | Int Dev 25.4 | `10.16.0.89:1521/pdevdb_demo.devprivatesn.devvcn.oraclevcn.com` |

Connection aliases live in `.env` (`INT_TRAIN_*`, `INT_DEV_*`). User/password inherit from `DEMO_DB_*`.

## Active 7 snapshots deployed

1. `FT_RPT_CURR`
2. `BSEG_BILLED_USAGE_RPT_CURR`
3. `BSEG_SQ_USAGE_RPT_CURR`
4. `D1_MSRMT_RPT_CURR`
5. `FT_GL_DISTRIBUTION_RPT_CURR`
6. `D1_USAGE_RPT_CURR`
7. `D1_USAGE_SCALAR_DTL_RPT_CURR`

## Steps completed (both DBs)

| Step | Script / command |
| --- | --- |
| Create tables | `01_create_all_active_snapshot_tables.sql` |
| Deploy baseline (full-history) procs | `02_deploy_all_initial_full_history_procedures.sql` |
| Run full baseline refresh | `03_run_all_initial_full_history_refreshes.sql` |
| Post-baseline validation | `04_validate_all_active_snapshots.sql` |
| Deploy 6-month rolling procs | `clients/citycorp/05_deploy_6month_rolling_window_updates.sql` |
| Run operational refresh | `clients/citycorp/06_run_operational_refreshes.sql` |
| Post-cutover validation | `04_validate_all_active_snapshots.sql` |

Logs:

- `deploy/snapshot_rollout_logs/int_train/baseline/full_refresh.log`
- `deploy/snapshot_rollout_logs/int_dev/baseline/full_refresh.log`

## Post-baseline row counts

| Snapshot | int_train | int_dev |
| --- | ---: | ---: |
| FT_RPT_CURR | 26,588 | 55,320 |
| BSEG_BILLED_USAGE_RPT_CURR | 3,817 | 19,646 |
| BSEG_SQ_USAGE_RPT_CURR | 10,552 | 19,021 |
| D1_MSRMT_RPT_CURR | 3,272,928 | 28,959 |
| FT_GL_DISTRIBUTION_RPT_CURR | 23,451 | 214 |
| D1_USAGE_RPT_CURR | 5,327 | 95 |
| D1_USAGE_SCALAR_DTL_RPT_CURR | 16,021 | 128 |

All seven tables populated on both databases after baseline refresh.

## QA notes

- `04_validate_all_active_snapshots.sql` completed successfully on both DBs after baseline and after 6-month cutover.
- **int_train** baseline install gate reported duplicate grain on `FT_RPT_CURR` (6,403 `ft_id` groups) and `D1_USAGE_SCALAR_DTL_RPT_CURR` (12 groups). Investigate before production scheduling on Train.
- **int_dev** duplicate-grain counts were zero; tables are clean on grain checks.

## Rerun commands

```bash
# Full internal install (tables + baseline + validate)
python3 scripts/local/run_snapshot_rollout_step.py \
  --step internal-7-baseline-and-validate --clients internal

# 6-month cutover + validate
python3 scripts/local/run_snapshot_rollout_step.py \
  --step internal-7-cutover-6month-and-validate --clients internal
```

Single-client example:

```bash
python3 scripts/local/run_client_oracle_sql.py --client int_train \
  --sql "SELECT COUNT(*) FROM cisadm.ft_rpt_curr"
```
