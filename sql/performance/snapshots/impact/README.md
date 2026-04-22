# Snapshot Impact Pack

## Purpose
This folder contains read-only SQL for measuring the database impact of the governed snapshot family.

Use it to answer:
- how large each snapshot is
- how current each snapshot is
- how refresh jobs are behaving
- which columns look sparse or low-value and should be reviewed for trimming

## Scripts
- `01_snapshot_inventory.sql`: object inventory, table stats, estimated row-based footprint
- `02_snapshot_storage_and_stats.sql`: table and index segment footprint by snapshot
- `03_snapshot_row_counts_and_freshness.sql`: live row counts and `LOAD_DTTM` freshness
- `04_snapshot_scheduler_health.sql`: scheduler jobs and recent run history
- `05_snapshot_column_relevance.sql`: stats-based column sparsity and low-value review
- `06_snapshot_sql_usage_optional.sql`: optional SQL usage review from `V$SQLAREA`
- `07_snapshot_sql_usage_averages.sql`: observed average elapsed time, CPU, logical reads, and physical reads per execution
- `08_snapshot_sql_usage_share.sql`: relative CPU, logical I/O, and physical I/O share within the snapshot family
- `09_snapshot_scheduler_runtime_averages.sql`: observed average, median, and max scheduler runtime by snapshot job
- `10_snapshot_storage_footprint_summary.sql`: table and index footprint summary for capacity planning
- `10b_snapshot_storage_footprint_user_views_fallback.sql`: fallback exact footprint query for CISADM-connected sessions without `ALL_SEGMENTS` access
- `11_snapshot_table_stats_density.sql`: row count, average row length, and estimated data payload by snapshot
- `12_snapshot_scheduler_configuration.sql`: configured scheduler cadence and current scheduler state
- `13_snapshot_resource_planning_summary.sql`: combined observed usage and storage summary for one-page planning packs
- `14_snapshot_recent_run_timeline.sql`: latest observed run per snapshot job plus recent cross-job run timeline
- `15_latest_active_snapshot_runs.sql`: most recent run and next run date for the current 7 active staggered snapshot jobs
- `16_snapshot_access_verification.sql`: verify current user, roles, and grants before running diagnostics

## Operating model
- All scripts are read-only.
- No DDL, DML, or `EXPLAIN PLAN`.
- Run in DEV or QA first.
- Use current optimizer stats where possible so null-density and NDV checks are meaningful.
- Treat `V$SQLAREA`-based outputs as observed sample evidence, not full-lifecycle guarantees.
- Distinguish refresh runtime from end-user query runtime when writing conclusions.
- `ALL_SEGMENTS` / `ALL_INDEXES` access is not guaranteed in every reporting account. If exact storage scripts fail with `ORA-00942`, use the `10b` fallback when connected as CISADM, or fall back to `11_snapshot_table_stats_density.sql` for estimated data size.

## Recommended workflow
1. Run `01_snapshot_inventory.sql`.
2. Run `02_snapshot_storage_and_stats.sql`.
3. Run `03_snapshot_row_counts_and_freshness.sql`.
4. Run `04_snapshot_scheduler_health.sql`.
5. Run `05_snapshot_column_relevance.sql`.
6. Run `06_snapshot_sql_usage_optional.sql` only if the account has the required catalog access.
7. Run `07_snapshot_sql_usage_averages.sql` for average-per-execution resource evidence.
8. Run `08_snapshot_sql_usage_share.sql` to compare relative CPU and I/O demand.
9. Run `09_snapshot_scheduler_runtime_averages.sql` for measured refresh-window cost.
10. Run `10_snapshot_storage_footprint_summary.sql` and `11_snapshot_table_stats_density.sql` for storage sizing.
11. Run `12_snapshot_scheduler_configuration.sql` to document configured cadence.
12. Run `13_snapshot_resource_planning_summary.sql` last if a one-page combined view is needed.
13. Run `14_snapshot_recent_run_timeline.sql` when you need the latest run order and durations before deeper testing.
