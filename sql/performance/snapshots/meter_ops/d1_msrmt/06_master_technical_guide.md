# D1_MSRMT_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed final-measurement snapshot `CISADM.D1_MSRMT_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug population, install-event, service-point, and lookup issues
- understand the final post-QA end state without reconstructing it from multiple files

## Final End State
Object summary:
- table: `CISADM.D1_MSRMT_RPT_CURR`
- grain: one row per processed measurement in `D1_MSRMT`
- natural key: `MEASR_COMP_ID`, `MSRMT_DTTM`
- refresh procedure: `CISADM.REFRESH_D1_MSRMT_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/meter_ops/d1_msrmt/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `D1_MSRMT_RPT_CURR`
- refresh pattern: `TRUNCATE + INSERT + COMMIT`
- scheduler interval: every 6 hours
- source population: all rows in `CISADM.D1_MSRMT`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed meter-operations reporting layer for final processed measurements.

It answers questions like:
- what final measurement value the system stored
- which measuring component produced the measurement
- which install event and service point were valid when the measurement occurred
- what IMD lineage, route, cycle, address, market, and division context applied

It is intentionally a measurement-grain object.

It is not for:
- raw inbound IMD history as the driving grain
- field-activity workflow reporting
- one-row-per-service-point summaries that ignore repeated measurements over time

## Original Design Problem
The older reporting approach mixed measurement, measuring-component, install-event, service-point, and field-activity logic in Jasper-side design.

What that older approach did well:
- exposed useful meter and service-point context
- surfaced measurement and IMD lineage fields
- supported exploratory operations reporting

What was wrong or insufficient about the older approach:
1. It risked fan-out when install-event and activity joins were not governed at Oracle grain.
2. It relied on runtime reporting joins for history-sensitive service-point context.
3. It mixed activity/process thinking into a measurement-grain reporting problem.
4. It did not provide one operational package with refresh, validation, and QA evidence.

## What Was Corrected In The Final Snapshot
The final governed snapshot fixes those issues in these specific ways.

### 1. The grain is explicit and enforced
The final governed object is one row per processed measurement in `D1_MSRMT`.

### 2. The reporting logic now lives in Oracle
The final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation SQL
- repeatable intensive QA SQL

### 3. Install-event context is time-valid
The procedure does not use a naive current-state install-event join.

Instead, it resolves the install event whose date window is valid at `MSRMT_DTTM` and uses a `NOT EXISTS` tie-breaker so only one install event is chosen for the measurement.

### 4. Activity/process joins were intentionally removed
`D1_ACTIVITY` and related field-operations joins are out of scope because they are a different business grain and create fan-out risk.

### 5. Code-only business fields were reviewed and accepted
The final release intentionally keeps these fields as code-only:
- `DIVISION_CD`
- `MKT_CD`
- `IMD_BO_STATUS_REASON_CD`
- `MC_BO_STATUS_REASON_CD`
- `MSRMT_BO_STATUS_REASON_CD`
- `SP_BO_STATUS_REASON_CD`

They are accepted for traceability and are not release blockers.

## Design Promise
The design promise is:

"For each processed measurement in `D1_MSRMT`, publish exactly one row with the stored measurement values, IMD lineage, measuring-component context, and the install/service-point context that was valid when the measurement occurred."

That means:
- the driver is `D1_MSRMT`
- the snapshot preserves the full processed measurement population
- install and service-point context are historically aligned to the measurement timestamp
- activity/process tables are intentionally excluded

## Population Boundary
Current governed population:

```sql
FROM cisadm.d1_msrmt msrmt
```

Included population:
- all `D1_MSRMT` rows

Excluded population:
- none

## Grain And Join Safety Rules
The grain is one row per `MEASR_COMP_ID`, `MSRMT_DTTM`.

This is protected by:
- driving directly from `D1_MSRMT`
- using `LEFT JOIN`s for IMD, measuring component, install event, and service point context
- resolving install events through time-valid conditions tied to `MSRMT_DTTM`
- choosing one valid install event through the `NOT EXISTS` tie-breaker

This prevents:
- duplicate measurement rows from multiple install events
- current-state service-point joins distorting historical measurements
- activity/process fan-out

## Final Refresh Procedure
The final procedure implementation is in `01_refresh_snapshot_procedure.sql`.

The final procedure behavior is:
- truncate the snapshot table
- insert the full governed measurement population from `D1_MSRMT`
- enrich with IMD, measuring component, time-valid install event, and service point context
- stamp `LOAD_DTTM` with `SYSTIMESTAMP`
- commit once

The time-valid install-event rule is:

```sql
LEFT JOIN cisadm.d1_install_evt ie
    ON ie.device_config_id = mc.device_config_id
   AND (ie.d1_install_dttm IS NULL OR ie.d1_install_dttm <= msrmt.msrmt_dttm)
   AND (ie.d1_removal_dttm IS NULL OR ie.d1_removal_dttm > msrmt.msrmt_dttm)
```

The single-row tie-breaker is enforced through the `NOT EXISTS` block in the procedure.

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_MSRMT_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh final measurement reporting snapshot every 6 hours'
    );
END;
/
```

## Domain Contract
The final Domain is a single-table JDBC Domain on `D1_MSRMT_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Implementation facts:
- file name: `D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- top-level reporting shape: single physical table, no Domain-side join tree
- intended user view: measurement, IMD, measuring component, install event, and service point context in one governed layer

## Validation And QA Approach
The package validates:
- source and snapshot measurement counts
- anti-joins both directions
- duplicate natural-key checks
- install/service-point context coverage behavior
- review of code-only fields that do not have translated description columns

Validation files:
- `03_validation_queries.sql`
- `04_intensive_qa_queries.sql`
- `05_qa_results_template.md`

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source measurement count: `1,680,216`
- snapshot measurement count: `1,680,216`
- count difference: `0`
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`

### Natural-key safety
- duplicate natural-key rows: `0 rows returned`

### Install / service-point coverage interpretation
The QA coverage block returned:
- source-side joined rows: `1,711,246`
- snapshot rows: `1,680,216`

That source-side count is higher than the actual measurement population, so it is not a valid population baseline. It proves the QA query's source join faned out `D1_MSRMT` through multiple install-event rows.

Interpretation:
- the snapshot is not dropping measurements because the top-level count parity and both anti-joins are exact
- the procedure's time-valid single-install-event logic is more precise than the broad QA comparison join
- the coverage block should be read as a reminder about install-event fan-out risk, not as a release blocker

### Accepted code-only fields
- `DIVISION_CD`: accepted without description
- `MKT_CD`: accepted without description
- `IMD_BO_STATUS_REASON_CD`: accepted without description
- `MC_BO_STATUS_REASON_CD`: accepted without description
- `MSRMT_BO_STATUS_REASON_CD`: accepted without description
- `SP_BO_STATUS_REASON_CD`: accepted without description

## Deployment Or Replication Steps
1. Run `00_create_snapshot_table.sql` in Oracle.
2. Create or replace the procedure with `01_refresh_snapshot_procedure.sql`.
3. Create the scheduler job with `02_schedule_snapshot_job.sql`.
4. Run a manual refresh:

```sql
BEGIN
    cisadm.refresh_d1_msrmt_rpt_curr;
END;
/
```

5. Run `03_validation_queries.sql`.
6. Run `04_intensive_qa_queries.sql`.
7. Import or reimport `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`.

## Debugging Guidance
Use SQL Developer to inspect the current state:

```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_msrmt_rpt_curr;
```

```sql
SELECT *
FROM cisadm.d1_msrmt_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_MSRMT_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;
```

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No`
- Needs population change: `No`
- Keep code-only fields as-is: `Yes`
