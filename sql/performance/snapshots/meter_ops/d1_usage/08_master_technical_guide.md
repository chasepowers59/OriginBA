# D1_USAGE_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed usage-header snapshot `CISADM.D1_USAGE_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug population, bridge, and refresh issues
- understand the final post-QA end state without reconstructing it from multiple files

## Final End State
Object summary:
- table: `CISADM.D1_USAGE_RPT_CURR`
- grain: one row per `D1_USAGE.D1_USAGE_ID`
- natural key: `D1_USAGE_ID`
- refresh procedure: `CISADM.REFRESH_D1_USAGE_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/meter_ops/d1_usage/D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `D1_USAGE_RPT_CURR`
- refresh pattern: `DELETE + monthly batched INSERT + COMMIT`
- scheduler interval: every 6 hours
- source population: all `D1_USAGE` rows where `NVL(START_DTTM, NVL(CRE_DTTM, STATUS_UPD_DTTM)) IS NOT NULL`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed usage-header reporting layer for meter operations.

It answers questions like:
- how many usage transactions exist
- what status and status timing those transactions have
- which usage subscriptions, cycles, routes, and service providers they belong to
- whether the usage header was used on bill or linked to a frozen bill segment
- how the usage header bridged into `C1_USAGE`, `CI_BSEG`, `CI_SA`, account, customer, and premise context when billing enrichment exists

It is intentionally a usage-header object.

It is not for:
- additive usage quantity reporting
- determinant-level `UOM_CD`, `TOU_CD`, `SQI_CD` analysis
- measuring-component-level usage detail
- full scalar-detail or period-SQ reporting

Those belong in `D1_USAGE_SCALAR_DTL_RPT_CURR` or another lower-grain usage artifact.

## Original Design Problem
The earlier usage reporting estate mixed usage header, scalar detail, period detail, billing, and customer context inside Jasper-side domain logic.

What that older approach did well:
- exposed useful usage-process fields
- exposed customer and billing context
- gave analysts one place to explore usage operations

What was wrong or insufficient about the older approach:
1. It blurred the real usage-header grain.
2. It risked row multiplication when lower-grain child tables were mixed into header reporting.
3. It relied on Jasper-side design instead of a governed Oracle-side snapshot contract.
4. It did not package refresh logic, validation logic, and QA evidence as one operationally supportable object family.

## What Was Corrected In The Final Snapshot
The final governed snapshot fixes those issues in these specific ways.

### 1. The grain is explicit and enforced
The final governed object is one row per `D1_USAGE_ID`.

### 2. The reporting logic now lives in Oracle
The final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation SQL
- repeatable intensive QA SQL

### 3. Billing linkage is optional enrichment, not driving truth
The final design preserves every qualifying usage header first, then overlays billing context through the canonical path:
- `D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID`
- restricted to `C1_USAGE.BO_STATUS_CD = 'BD-PROC'`

### 4. Lower-grain quantity logic was removed from the header snapshot
The final snapshot does not attempt to carry scalar-detail or period-SQ quantity logic.

### 5. Full-history refreshes are batched by month
The refresh uses the best available usage timestamp:
- `START_DTTM`
- then `CRE_DTTM`
- then `STATUS_UPD_DTTM`

### 6. Code-only business fields were reviewed and accepted as-is
The final snapshot intentionally keeps:
- `DIVISION_CD`
- `BO_STATUS_REASON_CD`
- `US_BO_STATUS_REASON_CD`

These fields remain code-only in this release. They are accepted for operational traceability and are not a release blocker.

## Design Promise
The design promise is:

"For each qualifying usage transaction in `D1_USAGE`, publish exactly one row with safe usage-header context and optional subscription, billing, service-agreement, account, customer, and premise enrichment, without changing the usage-header grain."

That means:
- the driver is `D1_USAGE`
- the snapshot preserves all qualifying usage headers
- billing context is optional
- lower-grain quantity facts are intentionally excluded

## Population Boundary
Current governed population:

```sql
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
```

Included population:
- all `D1_USAGE` rows with at least one usable timestamp among `START_DTTM`, `CRE_DTTM`, or `STATUS_UPD_DTTM`

Excluded population:
- only `D1_USAGE` rows with all three timestamps null

## Grain And Join Safety Rules
The grain is one row per `D1_USAGE_ID`.

This is protected by:
- driving from `D1_USAGE`
- using `LEFT JOIN`s for optional subscription and billing context
- resolving `C1_USAGE` through a ranked bridge subquery
- using one chosen customer row per account
- refusing to join scalar-detail and period-SQ detail into the header snapshot

This prevents:
- row multiplication from lower-grain child tables
- accidental population loss from optional enrichment joins
- mixed-grain reporting

## Final Table Contract
The final table implementation is defined in `01_create_snapshot_table.sql`.

The table carries four subject areas:
- core usage-header fields
- usage-subscription context
- billing-bridge context
- service agreement, account, customer, and premise context

Most important field decisions:
- `D1_USAGE_ID` is the natural key
- `BRIDGE_METHOD` and `C1_MATCH_COUNT` are kept for traceability
- `CUST_CL_DESC`, `COLL_CL_DESC`, `ACCT_MGMT_GRP_DESC`, and other stable description fields are persisted in Oracle
- `DIVISION_CD`, `BO_STATUS_REASON_CD`, and `US_BO_STATUS_REASON_CD` are intentionally kept as code-only
- quantity and determinant-detail fields are intentionally excluded

## Final Refresh Procedure
The final procedure implementation is in `02_refresh_snapshot_procedure.sql`.

The final procedure behavior is:
- clear the snapshot with `DELETE`
- detect the minimum and maximum batchable usage month from source
- load the snapshot month by month
- drive each batch from `D1_USAGE`
- enrich with subscription, billing bridge, bill segment, service agreement, account, customer, and premise context
- stamp `LOAD_DTTM` with `SYSTIMESTAMP`
- commit each month

Key implementation decisions:
- `DELETE` was kept instead of `TRUNCATE` so refreshes are less likely to fail with `ORA-00054` while the table is open in another session
- monthly batching was kept to reduce Oracle TEMP pressure during large rebuilds
- the `C1_USAGE` bridge is ranked with `ROW_NUMBER()` so one resolved bridge row is chosen per `D1_USAGE_ID`
- customer name is resolved through one ranked account-person row
- the three accepted code-only fields remain raw codes by design

The effective bridge rule is:

```sql
JOIN cisadm.c1_usage cu
    ON cu.usage_id = u.usg_ext_id
   AND cu.bo_status_cd = 'BD-PROC'
```

The batch driver rule is:

```sql
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= v_batch_start
  AND NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) < v_batch_end
```

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh usage header snapshot every 6 hours'
    );
END;
/
```

Operational meaning:
- refresh starts immediately when created
- then runs every 6 hours
- because the pattern is full rebuild by monthly batches, users should avoid querying during the refresh window if partial-refresh exposure matters

## Domain Contract
The final Domain is a single-table JDBC Domain on `D1_USAGE_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Exact final XML implementation facts:
- file name: `D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- top item group id: `D1_USAGE_RPT_CURR`
- top label: `Usage Header Snapshot`
- design approach: single physical table, no Domain-side join tree

Final item groups exposed:
- `D1_USAGE_CORE`
- `D1_USAGE_SUB`
- `D1_USAGE_BILLING`
- `D1_USAGE_CUSTOMER`
- `D1_USAGE_PREMISE`

Final exposure logic:
- the Domain reads the finished Oracle snapshot only
- both code and description are kept for most business dimensions where lookup coverage already exists
- the three accepted raw-code-only fields stay visible for traceability

## Build And Validation Workflow
### Build from scratch
1. Create the table using `01_create_snapshot_table.sql`.
2. Create or replace the procedure using `02_refresh_snapshot_procedure.sql`.
3. Run the manual refresh.
4. Run `04_validation_queries.sql`.
5. Run `05_status_cross_validation.sql`.
6. Run `06_intensive_qa_queries.sql`.
7. If validation and QA pass, create the scheduler job with `03_schedule_snapshot_job.sql`.
8. Publish or reimport the Domain XML.

### Manual refresh
```sql
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/
```

### Core checks
```sql
SELECT COUNT(*) AS snapshot_count
FROM cisadm.d1_usage_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_usage;
```

```sql
SELECT
    d1_usage_id,
    COUNT(*) AS row_count
FROM cisadm.d1_usage_rpt_curr
GROUP BY d1_usage_id
HAVING COUNT(*) > 1;
```

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source usage count: `684,214`
- snapshot usage count: `684,214`
- count difference: `0`
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`

### Monthly parity
- all `36` returned usage months matched exactly

### Billing bridge and context coverage
- rows with `C1_USAGE` in source: `623,557`
- rows with `C1_USAGE` in snapshot: `623,557`
- rows with `BSEG` in source: `623,366`
- rows with `BSEG` in snapshot: `623,366`
- rows with `SA` in source: `623,557`
- rows with `SA` in snapshot: `623,557`
- rows with `ACCT` in source: `623,557`
- rows with `ACCT` in snapshot: `623,557`
- all corresponding differences: `0`

### Accepted raw-code-only fields
The following expected description columns are not present in the snapshot table:
- `DIVISION_DESC`
- `BO_STATUS_REASON_DESC`
- `US_BO_STATUS_REASON_DESC`

Final interpretation:
- this is not a row-parity or bridge-logic defect
- this release accepts the corresponding code columns as-is
- future semantic enhancement can add descriptions later if needed

## SQL Developer Debugging Steps
### Check the table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_rpt_curr;
```

### Inspect sample rows
```sql
SELECT *
FROM cisadm.d1_usage_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

### View the procedure text
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_USAGE_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;
```

### View the scheduler job
```sql
SELECT owner,
       job_name,
       enabled,
       state,
       repeat_interval,
       last_start_date,
       next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_D1_USAGE_RPT_CURR';
```

## How To Debug Common Problems
### If row counts do not match source
Check:
1. whether the base source still uses `NVL(START_DTTM, NVL(CRE_DTTM, STATUS_UPD_DTTM)) IS NOT NULL`
2. whether someone changed a `LEFT JOIN` to an `INNER JOIN`
3. whether the batch window logic was altered
4. whether anti-join results identify missing or extra `D1_USAGE_ID` values

### If monthly parity drifts
Check:
1. whether the batch driver still uses the same best-available timestamp expression
2. whether the snapshot month still uses the same fallback ordering
3. whether a date conversion or truncation rule changed

### If billing bridge coverage looks wrong
Check:
1. whether the bridge still uses `USG_EXT_ID -> C1_USAGE.USAGE_ID`
2. whether `C1_USAGE.BO_STATUS_CD = 'BD-PROC'` is still enforced
3. whether the ranked bridge logic still returns only one chosen row per `D1_USAGE_ID`

### If descriptions are missing
Check:
1. whether the desc column is supposed to exist in the snapshot
2. whether the lookup join still points to the right source lookup table
3. whether the issue is a source lookup gap instead of a snapshot defect
4. whether the field is one of the accepted code-only fields in this release

## Final Status
`D1_USAGE_RPT_CURR` is approved as the governed usage-header snapshot.

It is:
- row-safe at usage-header grain
- fully reconciled to source for row counts and anti-joins
- validated for monthly parity
- validated for optional billing-bridge coverage
- operationally refreshable
- documented for replication and debugging
- acceptable for ad hoc and reporting use

The remaining semantic gap is limited to optional future description columns for accepted code-only fields. That is not a release blocker for the current design.
