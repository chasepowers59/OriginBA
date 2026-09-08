# SmartCity Demo (Int Demo 2.9) Snapshot Rollout

## Database

| Setting | Value |
| --- | --- |
| Host | `smartcity-db-demo.originsmartops.com` |
| Port | `1521` |
| Service | `pdemodb_demo.demoprivatesn2.origindemovcn.oraclevcn.com` |
| Client alias | `demo` (see `DEMO_*` in local `.env`) |

Connection test:

```bash
python3 scripts/local/run_client_oracle_sql.py --client demo --sql "select sysdate from dual"
```

## Tracker

Live status: [smartcity_demo_snapshot_rollout_status.md](smartcity_demo_snapshot_rollout_status.md)

## End-to-end flow (fresh demo database)

Use the standard deployment wrappers with `--clients demo`.

### Phase A — Build tables and load full history

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step preflight --clients demo
python3 scripts/local/run_snapshot_rollout_step.py --step create-tables --clients demo
python3 scripts/local/run_snapshot_rollout_step.py --step deploy-baseline-procs --clients demo
python3 scripts/local/run_snapshot_rollout_step.py --step schedule-baseline --clients demo
```

Baseline jobs are one-time scheduler loads staggered 15 minutes apart. They can run for hours. Poll status:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step baseline-status --clients demo
```

When all seven show `SUCCEEDED`, validate:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step validate --clients demo
```

### Phase B — 6-month rolling maintenance (no second full reload)

After baseline validation, deploy 6-month operational procedures and create recurring schedules only. Do **not** re-run full-history loads or a manual all-snapshot operational refresh.

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step deploy-6month-rolling --clients demo
python3 scripts/local/run_snapshot_rollout_step.py --step schedule-operational-6month --clients demo
python3 scripts/local/run_snapshot_rollout_step.py --step latest-runs --clients demo
```

The first scheduled job run applies the 6-month rolling window against the preserved baseline history.

## Notes

- Objects are created in schema `CISADM` (same as client test environments).
- Demo uses the shared `*_6month.sql` operational procedures wired through `deployment_steps/clients/citycorp/`.
- Store credentials only in `.env` (gitignored), not in committed files.
