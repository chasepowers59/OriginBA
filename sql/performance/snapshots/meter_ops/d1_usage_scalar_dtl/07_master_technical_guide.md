# D1_USAGE_SCALAR_DTL_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed scalar-detail usage snapshot `CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug population, quantity, bridge, and refresh issues
- understand the final post-QA end state without reconstructing it from multiple files

## Final End State
Object summary:
- table: `CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR`
- grain: one row per `D1_USAGE_SCALAR_DTL` line
- natural key: `D1_USAGE_ID`, `SEQ_NUM`
- refresh procedure: `CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `D1_USAGE_SCALAR_DTL_RPT_CURR`
- refresh pattern: `DELETE + monthly batched INSERT + COMMIT`
- scheduler interval: daily at `03:30`
- source population: all scalar-detail rows whose parent `D1_USAGE` row has at least one usable timestamp among `START_DTTM`, `CRE_DTTM`, or `STATUS_UPD_DTTM`
- primary additive measures: `QUANTITY`, `FINAL_QUANTITY`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed scalar-detail quantity layer for meter operations.

It answers questions like:
- how much raw and final quantity exists by scalar-detail line
- how usage breaks down by raw and final `UOM`, `TOU`, and `SQI`
- which measuring component and service point produced the scalar quantity
- which usage header, usage subscription, bill segment, service agreement, account, customer, and premise context belongs to the scalar row

It is intentionally a scalar-detail object.

It is not for:
- one-row-per-usage-transaction counts
- usage-header-only process monitoring
- collapsing scalar lines back into one usage row while pretending the lower-grain quantity detail is still preserved

Those belong in `D1_USAGE_RPT_CURR`.

## Original Design Problem
The older usage reporting estate mixed usage header facts and lower-grain quantity detail inside Jasper-side reporting logic.

What that older approach did well:
- exposed useful usage, subscription, and customer context
- exposed quantity-bearing detail
- supported exploratory billing-linked usage analysis

What was wrong or insufficient about the older approach:
1. It did not isolate scalar-detail grain cleanly from usage-header grain.
2. It left quantity truth dependent on report-side design rather than a governed Oracle snapshot.
3. It did not package refresh, validation, and QA logic as one operationally supportable object.
4. It made it too easy to confuse header reporting and quantity-detail reporting.

## What Was Corrected In The Final Snapshot
The final governed snapshot fixes those issues in these specific ways.

### 1. The grain is explicit and enforced
The final governed object is one row per `D1_USAGE_SCALAR_DTL` line, keyed by `D1_USAGE_ID`, `SEQ_NUM`.

### 2. Quantity truth now lives in Oracle
The final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation SQL
- repeatable intensive QA SQL

### 3. Usage-header and billing context are enrichment, not the driving grain
The snapshot drives from scalar-detail rows and carries header, subscription, billing, SA, customer, and premise context onto each scalar row without changing the scalar-detail grain.

### 4. Billing linkage is optional and canonical
The billing bridge is limited to the accepted path:
- `D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID`
- restricted to `C1_USAGE.BO_STATUS_CD = 'BD-PROC'`

### 5. Code-only business fields were reviewed and accepted
The final release intentionally keeps these fields as code-only:
- `DIVISION_CD`
- `BO_STATUS_REASON_CD`
- `US_BO_STATUS_REASON_CD`

They are accepted for operational traceability and are not release blockers.

## Design Promise
The design promise is:

"For each qualifying scalar-detail line in `D1_USAGE_SCALAR_DTL`, publish exactly one row with additive raw and final quantity plus safe usage, subscription, billing, service-agreement, account, customer, and premise context, without changing scalar-detail grain."

That means:
- the driver is `D1_USAGE_SCALAR_DTL`
- one row equals one scalar sequence
- `QUANTITY` and `FINAL_QUANTITY` remain additive at scalar-detail grain
- header and billing context are support fields, not the grain

## Population Boundary
Current governed population is based on the parent usage timestamp rule:

```sql
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
```

Included population:
- all scalar-detail rows whose parent usage satisfies the timestamp rule

Excluded population:
- only scalar-detail rows whose parent usage has all three batch-driving timestamps null

## Grain And Join Safety Rules
The grain is one row per `D1_USAGE_ID`, `SEQ_NUM`.

This is protected by:
- driving from `D1_USAGE_SCALAR_DTL`
- batching from parent `D1_USAGE` month windows
- using `LEFT JOIN`s for optional subscription, billing, customer, and premise context
- resolving the `C1_USAGE` bridge through one ranked match per `D1_USAGE_ID`
- resolving one chosen customer row per account

This prevents:
- row multiplication from customer joins
- accidental loss of scalar rows from optional enrichments
- confusion between scalar quantity truth and usage-header truth

## Final Table Contract
The final table implementation is defined in `01_create_snapshot_table.sql`.

The table carries five subject areas:
- snapshot audit fields
- usage-header context
- scalar-detail quantity and measurement context
- usage-subscription context
- optional billing, SA, customer, and premise context

Most important field decisions:
- `D1_USAGE_ID`, `SEQ_NUM` are the natural key
- `QUANTITY` and `FINAL_QUANTITY` are the additive measures
- raw and final `UOM`, `TOU`, and `SQI` are both preserved
- `BRIDGE_METHOD` and `C1_MATCH_COUNT` are kept for traceability
- `DIVISION_CD`, `BO_STATUS_REASON_CD`, and `US_BO_STATUS_REASON_CD` remain code-only by accepted business decision

## Final Refresh Procedure
The final procedure implementation is in `02_refresh_snapshot_procedure.sql`.

The final procedure behavior is:
- clear the snapshot with `DELETE`
- find the minimum and maximum batchable usage month from source
- load the snapshot month by month
- drive each batch from `D1_USAGE`
- join to `D1_USAGE_SCALAR_DTL` for the scalar-detail rows
- enrich with usage, subscription, billing bridge, bill segment, SA, account, customer, and premise context
- stamp `LOAD_DTTM` with `SYSTIMESTAMP`
- commit each month

Key implementation decisions:
- `DELETE` was kept instead of `TRUNCATE`
- monthly batching was kept to reduce Oracle pressure during full-history rebuilds
- the `C1_USAGE` bridge is ranked so one resolved bridge row is chosen per `D1_USAGE_ID`
- customer name is resolved through one ranked account-person row
- the three accepted code-only fields remain raw codes by design

The effective batch driver rule is:

```sql
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= v_batch_start
  AND NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) < v_batch_end
```

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB (
        job_name        => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=3;BYMINUTE=30;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh D1 usage scalar-detail reporting snapshot daily'
    );
END;
/
```

## Domain Contract
The final Domain is a single-table JDBC Domain on `D1_USAGE_SCALAR_DTL_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Implementation facts:
- file name: `D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- top item group id: `D1_USAGE_SCALAR_DTL_RPT_CURR`
- top label: `Usage Scalar Detail Snapshot`
- design approach: single physical table, no Domain-side join tree

The Domain intentionally exposes:
- usage-header context
- scalar-detail quantity fields
- final quantity output fields
- subscription context
- billing bridge context
- SA/customer context
- premise context

## Validation And QA Approach
The package validates:
- source and snapshot scalar counts
- anti-joins both directions
- additive `QUANTITY` parity
- additive `FINAL_QUANTITY` parity
- natural-key preservation at `D1_USAGE_ID`, `SEQ_NUM`
- code-only field review for accepted untranslated dimensions

Validation files:
- `04_validation_queries.sql`
- `05_intensive_qa_queries.sql`
- `06_qa_results_template.md`

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source scalar count: `720,071`
- snapshot scalar count: `720,071`
- count difference: `0`
- source `QUANTITY`: `8.6068E+10`
- snapshot `QUANTITY`: `8.6068E+10`
- `QUANTITY` difference: `0`
- source `FINAL_QUANTITY`: `8.6068E+10`
- snapshot `FINAL_QUANTITY`: `8.6068E+10`
- `FINAL_QUANTITY` difference: `0`

### Anti-joins and key safety
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`
- duplicate `D1_USAGE_ID`, `SEQ_NUM` rows: `0 implied by exact row parity plus zero anti-joins on the natural key`

### Accepted code-only fields
- `BO_STATUS_REASON_CD`: accepted without description
- `DIVISION_CD`: accepted without description
- `US_BO_STATUS_REASON_CD`: accepted without description

Interpretation:
- the snapshot preserves scalar-detail population and additive quantity truth exactly
- the remaining missing description columns are accepted business choices, not snapshot defects

## Deployment Or Replication Steps
1. Run `01_create_snapshot_table.sql` in Oracle.
2. Create or replace the procedure with `02_refresh_snapshot_procedure.sql`.
3. Create the scheduler job with `03_schedule_snapshot_job.sql`.
4. Run a manual refresh:

```sql
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/
```

5. Run `04_validation_queries.sql`.
6. Run `05_intensive_qa_queries.sql`.
7. Import or reimport `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`.

## Debugging Guidance
Use SQL Developer to inspect the current state:

```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;
```

```sql
SELECT *
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;
```

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No`
- Needs population change: `No`
- Keep code-only fields as-is: `Yes`
