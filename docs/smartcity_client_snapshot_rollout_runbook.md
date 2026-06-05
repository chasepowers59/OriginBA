# SmartCity Client Snapshot Rollout Runbook

## Scope

This runbook covers the active 7 governed snapshot tables for SmartCity client
test databases:

- `FT_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `BSEG_SQ_USAGE_RPT_CURR`
- `D1_MSRMT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_USAGE_RPT_CURR`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`

## Rollout Status Ledger

Current client-by-client rollout status and QA results are documented in:

- [smartcity_client_snapshot_rollout_status_2026-04-30.md](smartcity_client_snapshot_rollout_status_2026-04-30.md)

Recurring 6-hour schedules should not be created for a client until the status
ledger shows that all 7 baseline jobs completed and high-level QA has passed.

## Client Aliases

Use the client-aware runner:

```bash
python3 scripts/local/run_client_oracle_sql.py --client ellensburg --sql "select sysdate from dual"
```

Supported clients:

- `newark`
- `fonddulac`
- `collegestation`
- `ellensburg`
- `citycorp`

## Environment Status

`ellensburg` is the reference environment where the active 7 snapshot objects
were already built, tested, optimized, and scheduled during earlier work.

For the next client rollout, use Ellensburg for:

- connection sanity checks
- object and scheduler comparison
- expected validation-output shape
- runtime baseline reference

Do not treat Ellensburg as a fresh deployment target unless the intent is to
rebuild that environment.

Fresh rollout targets:

- `newark`
- `fonddulac`
- `collegestation`
- `citycorp`

## Deployment Flow

Use this sequence per fresh client.

For a single client, use `run_client_oracle_sql.py`.

For the four fresh rollout clients together, use `run_snapshot_rollout_step.py`.
The keyword `fresh` means:

- `newark`
- `fonddulac`
- `collegestation`
- `citycorp`

1. Access and environment preflight

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/impact/16_snapshot_access_verification.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step preflight --clients fresh
```

2. Create active snapshot tables

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/01_create_all_active_snapshot_tables.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step create-tables --clients fresh
```

3. Deploy initial full-history procedures

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step deploy-baseline-procs --clients fresh
```

4. Schedule unattended one-time full-history baseline jobs

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/03a_schedule_all_initial_full_history_refreshes.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step schedule-baseline --clients fresh
```

The one-time baseline jobs start immediately and then continue at 15-minute
intervals.

5. Capture status after the scheduled windows have had time to run

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/03b_capture_initial_full_history_job_status.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step baseline-status --clients fresh
```

6. Validate baseline snapshot contents

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql
```

Fresh-client batch form — recommended install gate:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step baseline-and-validate --clients fresh
```

Legacy single-step form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step validate --clients fresh
```

7. Deploy rolling-window operational procedures

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/05_deploy_all_rolling_window_updates.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step deploy-rolling-procs --clients fresh
```

8. Run operational refreshes once

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/06_run_all_operational_refreshes.sql
```

Fresh-client batch form — recommended cutover gate:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step cutover-and-validate --clients fresh
```

Or operational refresh + validate only:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step operational-and-validate --clients fresh
```

9. Validate again after rolling procedure cutover

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql
```

10. Create recurring 6-hour schedules

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/07_schedule_all_active_snapshots.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step schedule-operational --clients fresh
```

11. Capture recurring job configuration and latest runs

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/08_capture_latest_active_snapshot_runs.sql
```

Fresh-client batch form:

```bash
python3 scripts/local/run_snapshot_rollout_step.py --step latest-runs --clients fresh
```

## Dry Run

Before executing a wrapper, resolve includes and count statements:

```bash
python3 scripts/local/run_client_oracle_sql.py \
  --client ellensburg \
  --file sql/performance/snapshots/deployment_steps/01_create_all_active_snapshot_tables.sql \
  --dry-run
```

Batch dry-run example:

```bash
python3 scripts/local/run_snapshot_rollout_step.py \
  --step schedule-baseline \
  --clients fresh \
  --dry-run
```

## QA Requirements

Before deployment:

- confirm session user/schema
- confirm expected privileges
- confirm existing snapshot object state

After baseline jobs:

- all one-time baseline jobs should show `SUCCEEDED`
- row counts should be populated
- validation wrapper should pass for all 7 snapshots

After rolling procedure cutover:

- manual operational refresh should complete
- validation wrapper should pass again
- older baseline history should remain present
- recurring jobs should be scheduled on the 6-hour stagger

## Demo database (Int Demo 2.9)

**Jaspersoft imports:** use the environment promotion pipeline only — see
[jaspersoft_environment_promotion_pipeline.md](jaspersoft_environment_promotion_pipeline.md).
Every `origin_demo` ZIP automatically bundles the public dashboard template and
Development snapshot Domains (same fixes that made the full Standard Offering import succeed).

**Oracle snapshots:** fresh-database rollout (create tables, full-history baseline, then
6-month rolling schedules) is in
[smartcity_demo_snapshot_rollout_runbook.md](smartcity_demo_snapshot_rollout_runbook.md)
with live tracking in
[smartcity_demo_snapshot_rollout_status.md](smartcity_demo_snapshot_rollout_status.md).

Use client alias `demo` and store connection settings in local `.env` as `DEMO_*`.

## CityCorp 6-Month Rolling Cutover

CityCorp uses a **6-month** rolling maintenance window for all 7 active snapshots
instead of the default 12-month window used on the other fresh rollout clients.

Deploy the CityCorp-specific 6-month procedures, run one operational refresh,
then create the recurring 6-hour schedules:

```bash
python3 scripts/local/run_snapshot_rollout_step.py \
  --step citycorp-deploy-6month-rolling \
  --clients citycorp

python3 scripts/local/run_snapshot_rollout_step.py \
  --step citycorp-run-operational \
  --clients citycorp

python3 scripts/local/run_client_oracle_sql.py \
  --client citycorp \
  --file sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql

python3 scripts/local/run_snapshot_rollout_step.py \
  --step citycorp-schedule-operational \
  --clients citycorp
```

6-month procedure sources live beside the standard operational scripts as
`*_6month.sql` files and are wired through
`sql/performance/snapshots/deployment_steps/clients/citycorp/`.

## Assumptions

- The same schema owner, `CISADM`, is used in each test database.
- Client aliases in `.env` point to the correct test services.
- The first full-history procedures are used only for initial baseline seeding.
- The operational procedures preserve history and maintain the rolling windows.

## C2M And Jaspersoft Edge Cases

- Billing snapshots must preserve cancel/rebill behavior and determinant grain.
- FT snapshots must preserve transaction grain and GL distribution grain.
- D1 usage scalar detail has a wider effective grain than `(D1_USAGE_ID, SEQ_NUM)`.
- Jaspersoft Domains should not be repointed to these snapshots until the target
  client database has passed baseline and operational validation.

## TEMP Exhaustion Handling

If a baseline full-history job fails with `ORA-01652 unable to extend temp
segment`, do not assume the snapshot logic is wrong. This usually means the
single baseline load exceeded the client's available TEMP while aggregating a
large C2M history slice.

For `BSEG_BILLED_USAGE_RPT_CURR`, the full-history procedure is intentionally
batched by billing month. The procedure still truncates and rebuilds the full
target table, but each month:

- restricts the driving population to completed bills in that billing month
- aggregates `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` only for that
  month's eligible bill segments
- commits after the month finishes

This preserves the report grain of one row per `BSEG_ID` while reducing TEMP
pressure versus one global full-history insert. If a later month fails, rerun
the procedure after resolving capacity or load contention; it truncates the
target at the start and rebuilds from the beginning.

When retrying a failed baseline job:

- verify the procedure is `VALID`
- check `ALL_SCHEDULER_RUNNING_JOBS` first
- avoid stacking the retry on top of other active full-history jobs
- use `python3 scripts/local/run_snapshot_rollout_step.py --step retry-bseg-billed-baseline --clients <client>` to queue the retry two hours out
- validate row count, summed billed usage, summed initial usage, summed calc
  amount, and `COUNT(*) - COUNT(DISTINCT BSEG_ID)` after success
