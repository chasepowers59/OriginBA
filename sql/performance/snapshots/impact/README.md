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

## Operating model
- All scripts are read-only.
- No DDL, DML, or `EXPLAIN PLAN`.
- Run in DEV or QA first.
- Use current optimizer stats where possible so null-density and NDV checks are meaningful.

## Recommended workflow
1. Run `01_snapshot_inventory.sql`.
2. Run `02_snapshot_storage_and_stats.sql`.
3. Run `03_snapshot_row_counts_and_freshness.sql`.
4. Run `04_snapshot_scheduler_health.sql`.
5. Run `05_snapshot_column_relevance.sql`.
6. Run `06_snapshot_sql_usage_optional.sql` only if the account has the required catalog access.
