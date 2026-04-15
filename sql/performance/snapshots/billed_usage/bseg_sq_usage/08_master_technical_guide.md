# BSEG_SQ_USAGE_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed billed-usage determinant snapshot `CISADM.BSEG_SQ_USAGE_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- understand what was wrong with the original billed-usage approach
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug population, lookup, and refresh issues
- understand the final post-QA end state without reconstructing history from multiple artifacts

## Final End State
Object summary:
- table: `CISADM.BSEG_SQ_USAGE_RPT_CURR`
- grain: one row per completed-bill determinant key
- natural key: `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`
- refresh procedure: `CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR`
- scheduler job: `CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB`
- workspace Domain XML: `sql/performance/snapshots/billed_usage/bseg_sq_usage/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `BSEG_SQ_USAGE_RPT_CURR`
- refresh pattern: `TRUNCATE + INSERT + COMMIT`
- scheduler interval: every 6 hours
- source population: completed bill segments only, where `CI_BILL.BILL_STAT_FLG = 'C '`
- primary business measure: `TOTAL_BILL_SQ`
- supporting quantity field: `TOTAL_INIT_SQ`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed determinant-grain billed-usage layer for completed bill segments.

It answers questions like:
- how much billed quantity exists by determinant
- how billed usage breaks down by `UOM_CD`, `TOU_CD`, and `SQI_CD`
- which service types, customer classes, bill cycles, and premises those determinant rows belong to
- how many determinant outputs exist under each bill segment

It is intentionally the usage-truth layer for billed quantity detail.

It is not for:
- bill-segment billed amount truth
- additive determinant-level billed dollars
- charge allocation reporting

Those belong in `BSEG_BILLED_USAGE_RPT_CURR` or a future calc-line artifact.

## Intended Business Use
This snapshot should be used for determinant-grain billed-usage analysis.

The correct business stance is:
- use `TOTAL_BILL_SQ` as the primary safe measure
- use `TOTAL_INIT_SQ` as supporting determinant-level quantity context
- use `BSEG_BILLED_USAGE_RPT_CURR` when the main question is billed amount by bill segment

Why:
- determinant combinations are the natural billing-usage output grain
- many bill segments have multiple determinants
- forcing those determinants back into one segment row is fine for support context, but not for determinant-truth usage analysis
- additive billed dollars are not promised by this object

## Original Design Problem
The original billed-usage concept tried to answer both segment-level billing and determinant-level usage from one mixed reporting shape.

What that original approach did well:
- started from the correct billed-usage source, `CI_BSEG_SQ`
- carried useful bill, segment, account, and service context
- exposed determinant codes and billed quantities

What was wrong or insufficient about the original approach:
1. It did not clearly separate segment-level and determinant-level promises.
2. It risked mixing billed amount thinking into a determinant-grain artifact.
3. It did not package a repeatable Oracle-side refresh and QA contract.
4. It left too much ambiguity about which object should answer quantity questions and which should answer billed-dollar questions.

## What Was Corrected In The Final Snapshot
The final governed determinant snapshot fixes those issues in these specific ways.

### 1. The grain is explicit
The final governed object is one row per:
- `BSEG_ID`
- `UOM_CD`
- `TOU_CD`
- `SQI_CD`

If multiple `CI_BSEG_SQ` rows exist for the same determinant key on the same segment, they are intentionally aggregated together.

Why this matters:
- determinant quantity remains additive
- users know exactly what one row means
- usage analysis does not depend on unstable ad hoc joins

### 2. Segment-level context is attached safely
The final procedure builds determinant rows first, then joins safe bill, segment, account, customer, and service context onto them.

Why this matters:
- determinant grain is preserved
- context is still available for slicing and debugging
- quantity truth stays stable

### 3. The completed-bill boundary is explicit
The final snapshot includes completed bills only.

Why this matters:
- billed usage truth should reflect completed billing
- in-flight or pending bill segments are an operations subject, not billed-truth reporting

### 4. The reporting logic now lives in Oracle
Instead of depending on report-side logic, the final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation and intensive QA SQL

Why this matters:
- support staff can inspect real DB objects
- refresh behavior is controlled and repeatable
- QA can be rerun on demand

### 5. The business use is now governed against the segment snapshot
The final design explicitly separates:
- `BSEG_BILLED_USAGE_RPT_CURR` for billed amount at segment grain
- `BSEG_SQ_USAGE_RPT_CURR` for determinant-grain billed quantity

Why this matters:
- users do not confuse rolled-up segment context with determinant truth
- quantity and dollar questions go to the right object

## Design Promise
The design promise is:

"For each completed-bill determinant key on a bill segment, publish exactly one row with additive billed quantity and safe bill, segment, account, and service context."

That means:
- the driver is aggregated `CI_BSEG_SQ`
- only completed bill segments are included
- determinant quantity is the primary truth carried by the object
- billed amount is intentionally not the primary promise

## Population Boundary
Current governed population:

```sql
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
   AND bill.bill_stat_flg = 'C '
```

Included population:
- completed-bill determinant rows only

Excluded population:
- incomplete or pending bills
- non-complete bill-header populations

Why this boundary was chosen:
- this snapshot is for completed billed-usage truth
- final billing should be separated from in-flight billing operations

## Grain And Join Safety Rules
The grain is one row per determinant key:
- `BSEG_ID`
- `UOM_CD`
- `TOU_CD`
- `SQI_CD`

This is protected by:
- aggregating `CI_BSEG_SQ` by determinant key before joining context
- inner joining to completed bill segments only
- using `LEFT JOIN`s for optional enrichment
- resolving customer name to one ranked row per account
- calculating `BSEG_DETERMINANT_COUNT` separately per segment rather than by multiplying the determinant rows

This prevents:
- determinant row multiplication
- accidental loss of determinant rows from unnecessary inner joins
- mixed-grain quantity outputs

## Final Table Contract
The final table DDL is:

```sql
CREATE TABLE cisadm.bseg_sq_usage_rpt_curr (
    bseg_id                           VARCHAR2(30)    NOT NULL,
    uom_cd                            VARCHAR2(30),
    uom_desc                          VARCHAR2(100),
    tou_cd                            VARCHAR2(30),
    tou_desc                          VARCHAR2(100),
    sqi_cd                            VARCHAR2(30),
    sqi_desc                          VARCHAR2(100),
    sq_line_count                     NUMBER(18,0),
    bseg_determinant_count            NUMBER(18,0),
    total_init_sq                     NUMBER(22,6),
    total_bill_sq                     NUMBER(22,6),
    load_dttm                         TIMESTAMP DEFAULT SYSTIMESTAMP,
    bill_id                           VARCHAR2(30),
    acct_id                           VARCHAR2(30),
    customer_name                     VARCHAR2(200),
    sa_id                             VARCHAR2(30),
    sa_type_cd                        VARCHAR2(30),
    sa_type_desc                      VARCHAR2(100),
    utility_type_cd                   VARCHAR2(10),
    prem_id                           VARCHAR2(30),
    bseg_stat_flg                     VARCHAR2(10),
    bseg_stat_desc                    VARCHAR2(100),
    bill_stat_flg                     VARCHAR2(10),
    bill_stat_desc                    VARCHAR2(100),
    bill_dt                           DATE,
    due_dt                            DATE,
    bseg_start_dt                     DATE,
    bseg_end_dt                       DATE,
    win_start_dt                      DATE,
    bseg_bill_cyc_cd                  VARCHAR2(10),
    bseg_bill_cyc_desc                VARCHAR2(100),
    bill_bill_cyc_cd                  VARCHAR2(10),
    bill_bill_cyc_desc                VARCHAR2(100),
    cust_cl_cd                        VARCHAR2(10),
    cust_cl_desc                      VARCHAR2(100),
    coll_cl_cd                        VARCHAR2(10),
    coll_cl_desc                      VARCHAR2(100),
    acct_mgmt_grp_cd                  VARCHAR2(10),
    acct_mgmt_grp_desc                VARCHAR2(100),
    bud_plan_cd                       VARCHAR2(10),
    bud_plan_desc                     VARCHAR2(100),
    est_sw                            VARCHAR2(5),
    closing_bseg_sw                   VARCHAR2(5),
    sq_override_sw                    VARCHAR2(5),
    item_override_sw                  VARCHAR2(5),
    can_rsn_cd                        VARCHAR2(10),
    can_rsn_desc                      VARCHAR2(100),
    rebill_seg_id                     VARCHAR2(30),
    can_bseg_id                       VARCHAR2(30),
    master_bseg_id                    VARCHAR2(30)
);
```

## Field Inventory With Meaning
### Core determinant fields
- `BSEG_ID`: parent bill segment
- `UOM_CD`, `UOM_DESC`: unit of measure
- `TOU_CD`, `TOU_DESC`: time of use
- `SQI_CD`, `SQI_DESC`: service quantity identifier
- `SQ_LINE_COUNT`: number of source SQ rows aggregated into this determinant row
- `BSEG_DETERMINANT_COUNT`: number of distinct determinant keys on the segment
- `TOTAL_INIT_SQ`: determinant-level initial quantity
- `TOTAL_BILL_SQ`: determinant-level billed quantity
- `LOAD_DTTM`: snapshot load timestamp

### Bill and segment context
- `BILL_ID`
- `ACCT_ID`
- `CUSTOMER_NAME`
- `SA_ID`
- `SA_TYPE_CD`, `SA_TYPE_DESC`
- `UTILITY_TYPE_CD`
- `PREM_ID`
- `BSEG_STAT_FLG`, `BSEG_STAT_DESC`
- `BILL_STAT_FLG`, `BILL_STAT_DESC`
- `BILL_DT`
- `DUE_DT`
- `BSEG_START_DT`
- `BSEG_END_DT`
- `WIN_START_DT`
- `BSEG_BILL_CYC_CD`, `BSEG_BILL_CYC_DESC`
- `BILL_BILL_CYC_CD`, `BILL_BILL_CYC_DESC`

### Account segmentation fields
- `CUST_CL_CD`, `CUST_CL_DESC`
- `COLL_CL_CD`, `COLL_CL_DESC`
- `ACCT_MGMT_GRP_CD`, `ACCT_MGMT_GRP_DESC`
- `BUD_PLAN_CD`, `BUD_PLAN_DESC`

### Segment flag and lineage fields
- `EST_SW`
- `CLOSING_BSEG_SW`
- `SQ_OVERRIDE_SW`
- `ITEM_OVERRIDE_SW`
- `CAN_RSN_CD`, `CAN_RSN_DESC`
- `REBILL_SEG_ID`
- `CAN_BSEG_ID`
- `MASTER_BSEG_ID`

## Final Refresh Procedure
The final procedure behavior is:
- truncate the snapshot table
- build determinant-grain rows from aggregated `CI_BSEG_SQ`
- join completed bill, segment, account, and service context
- stamp `LOAD_DTTM` with `SYSTIMESTAMP`

The core procedure structure is:

```sql
CREATE OR REPLACE PROCEDURE cisadm.refresh_bseg_sq_usage_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.bseg_sq_usage_rpt_curr';

    INSERT INTO cisadm.bseg_sq_usage_rpt_curr (...)
    SELECT
        sq_det.bseg_id,
        sq_det.uom_cd,
        uom_l.descr,
        sq_det.tou_cd,
        tou_l.descr,
        sq_det.sqi_cd,
        sqi_l.descr,
        sq_det.sq_line_count,
        sq_bseg_agg.bseg_determinant_count,
        sq_det.total_init_sq,
        sq_det.total_bill_sq,
        SYSTIMESTAMP,
        bseg.bill_id,
        bill.acct_id,
        cust_name.entity_name,
        bseg.sa_id,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa_type_base.svc_type_cd,
        bseg.prem_id,
        bseg.bseg_stat_flg,
        bseg_status_l.descr,
        bill.bill_stat_flg,
        bill_status_l.descr,
        bill.bill_dt,
        bill.due_dt,
        bseg.start_dt,
        bseg.end_dt,
        bseg.win_start_dt,
        bseg.bill_cyc_cd,
        bseg_bill_cyc_l.descr,
        bill.bill_cyc_cd,
        bill_bill_cyc_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.sq_override_sw,
        bseg.item_override_sw,
        bseg.can_rsn_cd,
        can_rsn_l.descr,
        bseg.rebill_seg_id,
        bseg.can_bseg_id,
        bseg.master_bseg_id
    FROM (
        SELECT
            sq.bseg_id,
            sq.uom_cd,
            sq.tou_cd,
            sq.sqi_cd,
            COUNT(*) AS sq_line_count,
            SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
            SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
           AND bill.bill_stat_flg = 'C '
        GROUP BY
            sq.bseg_id,
            sq.uom_cd,
            sq.tou_cd,
            sq.sqi_cd
    ) sq_det
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq_det.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = bseg.sa_id
    LEFT JOIN (...) cust_name
        ON cust_name.acct_id = bill.acct_id
       AND cust_name.rn = 1
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = bill.acct_id
    LEFT JOIN (...) sa_type_base
        ON sa_type_base.sa_type_cd = sa.sa_type_cd
    LEFT JOIN (...) sq_bseg_agg
        ON sq_bseg_agg.bseg_id = sq_det.bseg_id
    LEFT JOIN lookup tables ...
    ;

    COMMIT;
END;
/
```

## Why The Final Procedure Looks This Way
Specific final design decisions:
- `TRUNCATE` was kept because a short empty-window refresh was accepted and the simpler full rebuild pattern is faster and easier to support
- completed-bill filtering is applied at the base source join
- `CI_BSEG_SQ` is aggregated by determinant key before context joins so determinant grain stays stable
- `BSEG_DETERMINANT_COUNT` is computed separately per segment and repeated safely on each determinant row
- billed amount is intentionally not part of the determinant fact promise
- customer name is resolved to one ranked row per account instead of joining directly to all account-person rows

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.create_job (
        job_name        => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh billed usage determinant snapshot every 6 hours'
    );
END;
/
```

Operational meaning:
- refresh starts immediately when created
- then runs every 6 hours
- because the pattern is full rebuild, users should avoid querying during the refresh window if empty-table exposure matters

## Domain Contract
The final Domain is a single-table JDBC Domain on `BSEG_SQ_USAGE_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Exact final XML implementation facts:
- file name: `BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- top item group id: `BSEG_SQ_USAGE_RPT_CURR`
- top label: `Billed Usage By Determinant`
- physical source block: `<jdbcTable id="BSEG_SQ_USAGE_RPT_CURR" datasourceId="Origin_DEV_DS" datasourceTableName="BSEG_SQ_USAGE_RPT_CURR" schemaAlias="CISADM">`
- design approach: single physical table, no Domain-side join tree

Final item groups exposed:
- `BSEG_SQ_AUDIT`
- `BSEG_SQ_DETERMINANT`
- `BSEG_SQ_BILLING`
- `BSEG_SQ_CUSTOMER`
- `BSEG_SQ_SEGMENTATION`
- `BSEG_SQ_FLAGS`

Final exposure logic:
- determinant fields are the center of the Domain
- bill, segment, customer, and service context are included for slicing and support
- switch and lineage fields remain available for traceability
- billed-dollar fields are intentionally excluded from the snapshot promise

## Step-By-Step Replication
### Build from scratch
1. Create the table using the full DDL shown above.
2. Create the procedure using the procedure logic shown above.
3. Run the manual refresh:

```sql
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/
```

4. Run the validation queries listed in the next section.
5. Run the intensive QA pack listed after that.
6. If validation and QA pass, create the scheduler job.
7. Publish the Domain XML using the final field contract shown above.

## Validation SQL To Run
Run these in order after a manual refresh.

### Manual refresh
```sql
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/
```

### Snapshot row count
```sql
SELECT COUNT(*) AS snapshot_count
FROM cisadm.bseg_sq_usage_rpt_curr;
```

### Source row count
```sql
SELECT COUNT(*) AS source_count
FROM (
    SELECT
        sq.bseg_id,
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id,
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
);
```

### Duplicate determinant-key check
```sql
SELECT
    bseg_id,
    NVL(uom_cd, '~') AS uom_cd_key,
    NVL(tou_cd, '~') AS tou_cd_key,
    NVL(sqi_cd, '~') AS sqi_cd_key,
    COUNT(*) AS row_count
FROM cisadm.bseg_sq_usage_rpt_curr
GROUP BY
    bseg_id,
    NVL(uom_cd, '~'),
    NVL(tou_cd, '~'),
    NVL(sqi_cd, '~')
HAVING COUNT(*) > 1;
```

### Description coverage check
```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bill_stat_desc IS NULL AND bill_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_status_desc,
    SUM(CASE WHEN bseg_stat_desc IS NULL AND bseg_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN customer_name IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN bill_bill_cyc_desc IS NULL AND bill_bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_bill_cyc_desc,
    SUM(CASE WHEN bseg_bill_cyc_desc IS NULL AND bseg_bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_bill_cyc_desc,
    SUM(CASE WHEN uom_desc IS NULL AND uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_uom_desc,
    SUM(CASE WHEN tou_desc IS NULL AND tou_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_tou_desc,
    SUM(CASE WHEN sqi_desc IS NULL AND sqi_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sqi_desc
FROM cisadm.bseg_sq_usage_rpt_curr;
```

### Quantity reconciliation
```sql
SELECT
    SUM(total_bill_sq) AS snap_total_bill_sq,
    SUM(total_init_sq) AS snap_total_init_sq,
    SUM(sq_line_count) AS snap_sq_line_count
FROM cisadm.bseg_sq_usage_rpt_curr;
```

## Intensive QA SQL To Run
Run these after the validation layer.

Key sections in the QA pack:
- source vs snapshot determinant baseline
- anti-join counts
- overall additive quantity parity
- raw-code-only field audit

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source determinant row count: `3,745,478`
- snapshot determinant row count: `3,745,478`
- count difference: `0`
- source `TOTAL_INIT_SQ`: `3.3090E+10`
- snapshot `TOTAL_INIT_SQ`: `3.3090E+10`
- initial quantity difference: `0`
- source `TOTAL_BILL_SQ`: `3.3090E+10`
- snapshot `TOTAL_BILL_SQ`: `3.3090E+10`
- billed quantity difference: `0`

### Anti-joins and grain safety
- duplicate determinant rows: `0`
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`
- `SQ_LINE_COUNT` matched source validation count: `3,745,478`

### Description and lookup coverage
- bill status description missing rows: `0`
- bill segment status description missing rows: `0`
- SA type description missing rows: `0`
- customer name missing rows: `0`
- bill bill-cycle descriptions missing where code exists: `874,192`
- bseg bill-cycle descriptions missing where code exists: `945,555`
- UOM descriptions missing where code exists: `1,943,111`
- TOU descriptions missing where code exists: `3,745,478`
- SQI descriptions missing where code exists: `1,487,857`

Interpretation:
- numeric and determinant-grain truth passed
- remaining issues are source lookup maintenance or optional semantic cleanup, not blockers to using the snapshot for determinant quantity

## Final Decisions On Business Context
### Primary business measure
- `TOTAL_BILL_SQ` is the primary safe business measure for this snapshot

### Supporting field
- `TOTAL_INIT_SQ` is supporting determinant-level quantity context

### What this snapshot should not promise
- billed amount by determinant
- determinant-level dollar allocation
- bill-segment billed-dollar truth

### Why this decision was made
- determinant quantity is native to `CI_BSEG_SQ`
- billed dollars are not safely promised at this determinant artifact
- segment-level billed amount is governed separately in `BSEG_BILLED_USAGE_RPT_CURR`

### Keep in the snapshot
- raw utility type code
- switch fields
- bill and segment lineage IDs
- segment-level context fields repeated safely on determinant rows

## SQL Developer Debugging Steps
### Check the table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_sq_usage_rpt_curr;
```

### Inspect sample rows
```sql
SELECT *
FROM cisadm.bseg_sq_usage_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

### View the procedure text
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_BSEG_SQ_USAGE_RPT_CURR'
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
  AND job_name = 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB';
```

### Manual refresh
```sql
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/
```

## How To Debug Common Problems
### If row counts do not match source
Check:
1. whether the completed-bill filter is still present
2. whether determinant aggregation still groups by `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`
3. whether duplicate determinant keys were introduced
4. whether anti-join checks show missing or extra rows

### If quantity does not match source
Check:
1. whether `CI_BSEG_SQ` is still aggregated before context joins
2. whether `TOTAL_BILL_SQ` and `TOTAL_INIT_SQ` still come from the aggregated determinant source
3. whether row-multiplying joins were introduced

### If determinant descriptions are missing
Check:
1. whether the source code is populated
2. whether the corresponding lookup exists in the tenant source table
3. whether the issue is a source lookup gap instead of a snapshot defect

### If the Domain is missing fields
Check:
1. whether the column exists in Oracle
2. whether the field exists in the Domain XML
3. whether the Jaspersoft Domain was reimported after the change

## Final Status
`BSEG_SQ_USAGE_RPT_CURR` is approved as the governed billed-usage determinant snapshot.

It is:
- row-safe at determinant grain
- numerically reconciled to source
- operationally refreshable
- documented for replication and debugging
- appropriate for billed-usage quantity analysis at determinant grain

It should not be treated as the billed-dollar truth layer.
