# Snapshot Impact Assessment

## Current alignment
We are partially aligned, not fully aligned yet.

What is already aligned:
- snapshot grain is now documented per artifact
- trusted additive measures are documented
- XML artifacts are mapped to the snapshots
- several snapshots already document what was intentionally excluded
- read-only validation SQL exists for row safety and business correctness

What is not fully aligned yet:
- there was no single read-only DB impact pack for all snapshots
- there was no shared method to compare storage footprint across snapshots
- there was no shared method to review scheduler runtime and refresh behavior across snapshots
- there was no shared stats-based trim review to flag sparse or low-value columns across the snapshot family

This document closes that gap by defining how to inspect impact in the database and how to review "fat" in the snapshots.

## What impact means
For snapshots, "impact on the current database" should be measured in five ways:

1. Footprint
- how many rows each snapshot stores
- how much table segment space it consumes
- how much index space it consumes

2. Refresh cost
- how often the snapshot refresh runs
- how long the refresh jobs take
- whether refreshes are succeeding or failing

3. Freshness
- when the snapshot was last loaded
- whether the snapshot is stale compared with the expected schedule

4. Structural efficiency
- whether the snapshot is preserving the intended grain
- whether it duplicates rows
- whether it includes sparse or low-value columns that should be reviewed

5. Business value density
- whether each included field is relevant to the stated business use case
- whether optional overlays are being mistaken for additive truth

## DB checks to run
Use the read-only SQL pack in:
- `sql/performance/snapshots/impact/`

Recommended order:
1. `01_snapshot_inventory.sql`
2. `02_snapshot_storage_and_stats.sql`
3. `03_snapshot_row_counts_and_freshness.sql`
4. `04_snapshot_scheduler_health.sql`
5. `05_snapshot_column_relevance.sql`
6. `06_snapshot_sql_usage_optional.sql` when catalog-performance views are available

## How to interpret the results

### Healthy pattern
- table exists
- object status is valid
- row count is plausible for the grain
- load timestamp is recent
- scheduler jobs succeed on schedule
- segment size is proportionate to row count and purpose
- sparse columns are rare and justified

### Warning pattern
- refresh failures or long runtimes
- large storage growth with no business reason
- many columns that are almost always null
- columns with one distinct value across the full population
- snapshots carrying data better served by another grain

### Trim candidate pattern
Columns should be reviewed for removal or relocation when they are:
- effectively always null
- almost always null
- constant across the population
- wide text columns with very low business use
- duplicate business meaning already available in a cleaner field

That does not mean they must be deleted automatically. It means they need a relevance review with the business use case and XML consumers in mind.

## Important limits
- stats-based column review depends on current optimizer stats
- SQL usage review depends on access to `V$SQLAREA`
- segment and scheduler views depend on the privileges of the DB account running the checks
- trimming should never happen before confirming whether the field is used in XML, JRXML, reports, or ad hoc views

## Recommended next step
Run the impact pack in DEV or QA first, capture outputs by snapshot, then classify each column into:
- keep
- keep but move to another grain later
- review with business owner
- trim candidate

That is the cleanest way to prove both DB impact and relevance before making structural cuts.
