# BSEG_BILLED_USAGE_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed billed bill-segment snapshot `CISADM.BSEG_BILLED_USAGE_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- understand what was wrong with the original billed-usage domain approach
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug population, lookup, and refresh issues
- understand the final post-QA end state without reconstructing history from multiple artifacts

## Final End State
Object summary:
- table: `CISADM.BSEG_BILLED_USAGE_RPT_CURR`
- grain: one row per `CI_BSEG.BSEG_ID`
- refresh procedure: `CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/billed_usage/bseg_billed_usage/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `BSEG_BILLED_USAGE_RPT_CURR`
- refresh pattern: `TRUNCATE + INSERT + COMMIT`
- scheduler interval: every 6 hours
- source population: completed bill segments only, where `CI_BILL.BILL_STAT_FLG = 'C '`
- primary business measure: `TOTAL_CALC_AMT`
- supporting rolled-up quantity fields: `TOTAL_BILL_SQ`, `TOTAL_INIT_SQ`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed completed-bill bill-segment layer for billed amount reporting at `BSEG` grain.

It answers questions like:
- how many completed bill segments exist
- what billed amount is associated to each bill segment
- what service agreement, account, premise, customer, and billing context belongs to the segment
- what aggregated billed quantity, read, and rate context is associated to the segment

It is intentionally not the determinant-truth usage layer.

It is not for:
- usage by determinant as the primary reporting truth
- one row per `CI_BSEG_SQ`
- UOM/TOU/SQI analysis where exact determinant grain matters

Those belong in `BSEG_SQ_USAGE_RPT_CURR`.

## Intended Business Use
This snapshot should be used primarily for billed amount analysis at bill-segment grain.

The correct business stance is:
- use `TOTAL_CALC_AMT` as the primary safe measure
- treat `TOTAL_BILL_SQ` and `TOTAL_INIT_SQ` as rolled-up supporting context
- do not use this object as the main billed-usage truth layer when determinant detail matters

Why:
- one bill segment is represented by one snapshot row
- billed amount is rolled up cleanly to that row
- billed usage often contains multiple determinant combinations on the same bill segment
- collapsing many determinants into one row is fine for support context, but it is not the right truth layer for determinant-sensitive usage analysis

Evidence from validation:
- total completed bill segments: `2,214,878`
- rows with exactly one determinant: `985,799`
- therefore more than one million bill segments are not single-determinant rows

That is why this object is a billed-amount segment snapshot, not the main usage-detail snapshot.

## Original Design Problem
The original billed-usage concept tried to answer both bill-segment billing questions and determinant-level usage questions in one semantic shape.

What that original approach did well:
- started from the correct billing sources, especially `CI_BSEG`
- carried useful bill, segment, service, account, and customer context
- attempted to expose both billed amount and billed quantity

What was wrong or insufficient about the original approach:
1. It did not establish one clear grain.
   Bill headers, bill segments, service-quantity lines, reads, and calc headers were all candidates to drive the result.
2. It exposed a row-multiplication risk.
   Joining `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` directly to `CI_BSEG` can multiply segment rows.
3. It mixed billed-amount truth with determinant-level usage detail.
   Those are related but not the same reporting contract.
4. It was not operationally supportable.
   There was no single governed table plus procedure plus scheduler plus QA pack that another person could inspect and rerun.
5. It did not clearly distinguish what this object should and should not be used for.
   That is the main reason this guide is explicit about billed amount versus determinant usage.

## What Was Corrected In The Final Snapshot
The final governed billed-usage snapshot fixes the original design issues in these specific ways.

### 1. The grain is explicit
The final governed object is one row per `BSEG_ID`.

Why this matters:
- segment counts are stable
- billed amount rolls cleanly at one row per segment
- billing support has one consistent bill-segment record to debug

### 2. Child detail is aggregated before it joins the segment
The final refresh procedure aggregates:
- `CI_BSEG_SQ` to one segment-level row
- `CI_BSEG_READ` to one segment-level row
- `CI_BSEG_CALC` to one segment-level row

Why this matters:
- no child table is allowed to multiply the bill segment
- segment-level totals remain stable
- counts and sums reconcile cleanly

### 3. The population boundary is explicit
The final snapshot includes completed bills only.

Why this matters:
- billed truth should reflect completed billing
- incomplete or pending billing is an operations subject, not billed-truth reporting
- segment totals can be used more safely when the bill is complete

### 4. The reporting logic now lives in Oracle
Instead of depending on report-side or ad hoc join logic, the final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation and intensive QA SQL

Why this matters:
- DB and reporting support can inspect real objects
- refresh behavior is controlled and repeatable
- QA can be rerun on demand

### 5. The business use is now clearly governed
The final design explicitly says:
- billed amount at bill-segment grain is the intended use
- determinant-heavy usage analysis should use `BSEG_SQ_USAGE_RPT_CURR`

Why this matters:
- users do not confuse a rolled-up support field with determinant-truth usage
- the segment snapshot stays focused on its real business promise

## Design Promise
The design promise is:

"For each completed bill segment, publish exactly one row with stable billed-amount truth and safe segment-level billing context, while keeping rolled-up usage only as supporting context."

That means:
- the driver is `CI_BSEG`
- only completed bill segments are included
- service quantity, read, and calc tables are aggregated before they join
- the object is for billed amount at `BSEG` grain
- usage fields are supporting context, not the primary determinant-truth layer

## Population Boundary
Current governed population:

```sql
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
   AND bill.bill_stat_flg = 'C '
```

Included population:
- completed bill segments only

Excluded population:
- incomplete bills
- pending bills
- canceled or non-complete bill headers outside status `C `

Why this boundary was chosen:
- this snapshot is for billed truth
- final billing should be separated from in-flight billing operations

## Grain And Join Safety Rules
The grain is one row per `BSEG_ID`.

This is protected by:
- driving from `CI_BSEG`
- inner joining only to completed `CI_BILL`
- using `LEFT JOIN`s for optional enrichment
- aggregating `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` before joining them
- resolving customer name to one ranked row per account

This prevents:
- row multiplication from service-quantity, read, or calc detail
- accidental loss of bill segments from unnecessary inner joins
- mixed-grain billing outputs

## Final Table Contract
The final table DDL is:

```sql
CREATE TABLE cisadm.bseg_billed_usage_rpt_curr (
    bseg_id                           VARCHAR2(30)    NOT NULL,
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
    load_dttm                         TIMESTAMP DEFAULT SYSTIMESTAMP,
    cust_cl_cd                        VARCHAR2(10),
    cust_cl_desc                      VARCHAR2(100),
    coll_cl_cd                        VARCHAR2(10),
    coll_cl_desc                      VARCHAR2(100),
    acct_mgmt_grp_cd                  VARCHAR2(10),
    acct_mgmt_grp_desc                VARCHAR2(100),
    bud_plan_cd                       VARCHAR2(10),
    bud_plan_desc                     VARCHAR2(100),
    sq_line_count                     NUMBER(18,0),
    determinant_count                 NUMBER(18,0),
    total_init_sq                     NUMBER(22,6),
    total_bill_sq                     NUMBER(22,6),
    sole_uom_cd                       VARCHAR2(30),
    sole_uom_desc                     VARCHAR2(100),
    sole_tou_cd                       VARCHAR2(30),
    sole_tou_desc                     VARCHAR2(100),
    sole_sqi_cd                       VARCHAR2(30),
    sole_sqi_desc                     VARCHAR2(100),
    read_line_count                   NUMBER(18,0),
    total_msr_qty                     NUMBER(22,6),
    total_final_reg_qty               NUMBER(22,6),
    min_start_read_dttm               TIMESTAMP,
    max_end_read_dttm                 TIMESTAMP,
    calc_header_count                 NUMBER(18,0),
    total_calc_amt                    NUMBER(15,2),
    rs_count                          NUMBER(18,0),
    sole_rs_cd                        VARCHAR2(30),
    sole_rs_desc                      VARCHAR2(100),
    min_calc_effdt                    DATE,
    max_calc_effdt                    DATE,
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
### Core bill and segment fields
- `BSEG_ID`: natural key, one row per bill segment
- `BILL_ID`: parent bill header
- `ACCT_ID`: linked account
- `CUSTOMER_NAME`: resolved primary customer name
- `SA_ID`: linked service agreement
- `SA_TYPE_CD`, `SA_TYPE_DESC`: service type code and label
- `UTILITY_TYPE_CD`: raw service category code derived from service type setup
- `PREM_ID`: premise
- `BSEG_STAT_FLG`, `BSEG_STAT_DESC`: bill segment status
- `BILL_STAT_FLG`, `BILL_STAT_DESC`: bill status
- `BILL_DT`, `DUE_DT`: bill dates
- `BSEG_START_DT`, `BSEG_END_DT`, `WIN_START_DT`: billing window dates
- `BSEG_BILL_CYC_CD`, `BSEG_BILL_CYC_DESC`: segment bill cycle
- `BILL_BILL_CYC_CD`, `BILL_BILL_CYC_DESC`: bill header bill cycle
- `LOAD_DTTM`: snapshot load timestamp

### Account segmentation fields
- `CUST_CL_CD`, `CUST_CL_DESC`
- `COLL_CL_CD`, `COLL_CL_DESC`
- `ACCT_MGMT_GRP_CD`, `ACCT_MGMT_GRP_DESC`
- `BUD_PLAN_CD`, `BUD_PLAN_DESC`

### Aggregated service-quantity fields
- `SQ_LINE_COUNT`: number of SQ lines under the segment
- `DETERMINANT_COUNT`: distinct determinant combinations under the segment
- `TOTAL_INIT_SQ`: rolled-up initial quantity
- `TOTAL_BILL_SQ`: rolled-up billed quantity
- `SOLE_UOM_CD`, `SOLE_UOM_DESC`: only populated when one determinant exists
- `SOLE_TOU_CD`, `SOLE_TOU_DESC`: only populated when one determinant exists
- `SOLE_SQI_CD`, `SOLE_SQI_DESC`: only populated when one determinant exists

### Aggregated read fields
- `READ_LINE_COUNT`
- `TOTAL_MSR_QTY`
- `TOTAL_FINAL_REG_QTY`
- `MIN_START_READ_DTTM`
- `MAX_END_READ_DTTM`

### Aggregated billed-amount fields
- `CALC_HEADER_COUNT`
- `TOTAL_CALC_AMT`
- `RS_COUNT`
- `SOLE_RS_CD`, `SOLE_RS_DESC`
- `MIN_CALC_EFFDT`
- `MAX_CALC_EFFDT`

### Segment flags and lineage
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
- rebuild it from completed `CI_BSEG` rows
- aggregate SQ, read, and calc children before joining
- stamp `LOAD_DTTM` with `SYSTIMESTAMP`

The core procedure structure is:

```sql
CREATE OR REPLACE PROCEDURE cisadm.refresh_bseg_billed_usage_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.bseg_billed_usage_rpt_curr';

    INSERT INTO cisadm.bseg_billed_usage_rpt_curr (...)
    SELECT
        bseg.bseg_id,
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
        SYSTIMESTAMP,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        acct.bud_plan_cd,
        bud_plan_l.descr,
        sq_agg.sq_line_count,
        sq_agg.determinant_count,
        sq_agg.total_init_sq,
        sq_agg.total_bill_sq,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_uom_cd END,
        sole_uom_l.descr,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_tou_cd END,
        sole_tou_l.descr,
        CASE WHEN sq_agg.determinant_count = 1 THEN sq_agg.min_sqi_cd END,
        sole_sqi_l.descr,
        read_agg.read_line_count,
        read_agg.total_msr_qty,
        read_agg.total_final_reg_qty,
        read_agg.min_start_read_dttm,
        read_agg.max_end_read_dttm,
        calc_agg.calc_header_count,
        calc_agg.total_calc_amt,
        calc_agg.rs_count,
        CASE WHEN calc_agg.rs_count = 1 THEN calc_agg.min_rs_cd END,
        sole_rs_l.descr,
        calc_agg.min_calc_effdt,
        calc_agg.max_calc_effdt,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.sq_override_sw,
        bseg.item_override_sw,
        bseg.can_rsn_cd,
        can_rsn_l.descr,
        bseg.rebill_seg_id,
        bseg.can_bseg_id,
        bseg.master_bseg_id
    FROM cisadm.ci_bseg bseg
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
    LEFT JOIN (...) sq_agg
        ON sq_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (...) read_agg
        ON read_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (...) calc_agg
        ON calc_agg.bseg_id = bseg.bseg_id
    LEFT JOIN lookup tables ...
    ;

    COMMIT;
END;
/
```

## Why The Final Procedure Looks This Way
Specific final design decisions:
- `TRUNCATE` was kept because a short empty-window refresh was accepted and the simpler full rebuild pattern is faster and easier to support
- the bill-status filter is applied at the base join so only completed bill segments enter the snapshot
- `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` are aggregated before joining to preserve `BSEG` grain
- `TOTAL_CALC_AMT` is carried as the primary billed-amount field at segment grain
- determinant-only description fields are only populated when the segment has exactly one determinant
- sole rate description is only populated when the segment has exactly one rate schedule in calc context
- customer name is resolved to one ranked row per account instead of joining directly to all account-person rows

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh bill-segment billed usage snapshot every 6 hours'
    );
END;
/
```

Operational meaning:
- refresh starts immediately when created
- then runs every 6 hours
- because the pattern is full rebuild, users should avoid querying during the refresh window if empty-table exposure matters

## Domain Contract
The final Domain is a single-table JDBC Domain on `BSEG_BILLED_USAGE_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Exact final XML implementation facts:
- file name: `BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- top item group id: `BSEG_BILLED_USAGE_RPT_CURR`
- top label: `Billed Usage By Bill Segment`
- physical source block: `<jdbcTable id="BSEG_BILLED_USAGE_RPT_CURR" datasourceId="Origin_DEV_DS" datasourceTableName="BSEG_BILLED_USAGE_RPT_CURR" schemaAlias="CISADM">`
- design approach: single physical table, no Domain-side join tree

Final item groups exposed:
- `BSEG_CUSTOMER`
- `BSEG_BILLING`
- `BSEG_USAGE`
- `BSEG_DETERMINANTS`
- `BSEG_SEGMENTATION`
- `BSEG_READS`
- `BSEG_FLAGS`
- `BSEG_AUDIT`

Important usage note for the Domain:
- the group name `BSEG_USAGE` should not be read as determinant-truth usage
- in business use, `TOTAL_CALC_AMT` is the primary field to trust
- `TOTAL_BILL_SQ` and related quantity fields are rolled-up support fields only

## Why These Domain Fields Were Exposed
Final exposure logic:
- segment billing context is exposed because this is a bill-segment snapshot
- billed amount is exposed as the primary business measure
- rolled-up usage, read, and determinant hints are exposed for support context
- raw utility type and switch fields are kept for traceability, not because they are the main business dimensions

## Step-By-Step Replication
### Build from scratch
1. Create the table using the full DDL shown above.
2. Create the procedure using the procedure logic shown above.
3. Run the manual refresh:

```sql
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
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
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/
```

### Snapshot row count
```sql
SELECT COUNT(*) AS snapshot_count
FROM cisadm.bseg_billed_usage_rpt_curr;
```

### Source row count
```sql
SELECT COUNT(*) AS source_count
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';
```

### Duplicate natural-key check
```sql
SELECT
    bseg_id,
    COUNT(*) AS row_count
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY
    bseg_id
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
    SUM(CASE WHEN sole_uom_desc IS NULL AND sole_uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_uom_desc,
    SUM(CASE WHEN sole_tou_desc IS NULL AND sole_tou_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_tou_desc,
    SUM(CASE WHEN sole_sqi_desc IS NULL AND sole_sqi_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_sqi_desc,
    SUM(CASE WHEN sole_rs_desc IS NULL AND sole_rs_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_rs_desc
FROM cisadm.bseg_billed_usage_rpt_curr;
```

### Billed amount and quantity reconciliation
```sql
SELECT
    SUM(total_bill_sq) AS snap_total_bill_sq,
    SUM(total_init_sq) AS snap_total_init_sq,
    SUM(total_calc_amt) AS snap_total_calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr;
```

### Determinant distribution check
```sql
SELECT
    determinant_count,
    COUNT(*) AS bseg_count,
    SUM(total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY determinant_count
ORDER BY determinant_count;
```

## Intensive QA SQL To Run
Run these after the validation layer.

Key sections in the QA pack:
- source vs snapshot completed-segment baseline
- anti-join counts and sample `BSEG_ID` checks
- overall additive parity
- aggregated child parity for SQ, reads, and calc
- sole-description coverage when single-valued context exists
- raw-code-only field audit

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source completed `BSEG` count: `2,214,878`
- snapshot `BSEG` count: `2,214,878`
- count difference: `0`
- source `TOTAL_BILL_SQ`: `3.3090E+10`
- snapshot `TOTAL_BILL_SQ`: `3.3090E+10`
- quantity difference: `0`
- source `TOTAL_INIT_SQ`: `3.3090E+10`
- snapshot `TOTAL_INIT_SQ`: `3.3090E+10`
- initial quantity difference: `0`
- source `TOTAL_CALC_AMT`: `261,674,711`
- snapshot `TOTAL_CALC_AMT`: `261,674,711`
- billed amount difference: `0`

### Anti-joins and grain safety
- duplicate `BSEG_ID` rows: `0`
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`
- rows with SQ: `1,873,559 / 1,873,559`
- rows with reads: `623,115 / 623,115`
- rows with calc headers: `2,214,232 / 2,214,232`

### Description and lookup coverage
- bill status description missing rows: `0`
- bill segment status description missing rows: `0`
- SA type description missing rows: `0`
- customer name missing rows: `0`
- bill bill-cycle descriptions missing where code exists: `1,193,988`
- bseg bill-cycle descriptions missing where code exists: `1,214,889`
- single-determinant rows missing `SOLE_UOM_DESC` when required: `129,171`
- single-determinant rows missing `SOLE_TOU_DESC` when required: `985,799`
- single-determinant rows missing `SOLE_SQI_DESC` when required: `856,628`
- single-rate rows missing `SOLE_RS_DESC` when required: `31,306`

Interpretation:
- numeric and population truth passed
- remaining issues are source lookup maintenance or optional semantic cleanup, not blockers to using the snapshot for billed amount

## Final Decisions On Business Context
### Primary business measure
- `TOTAL_CALC_AMT` is the primary safe business measure for this snapshot

### Supporting but not primary fields
- `TOTAL_BILL_SQ`
- `TOTAL_INIT_SQ`
- `TOTAL_MSR_QTY`
- `TOTAL_FINAL_REG_QTY`
- determinant-only label fields such as `SOLE_UOM_DESC`, `SOLE_TOU_DESC`, `SOLE_SQI_DESC`, and `SOLE_RS_DESC`

### Why this decision was made
- one bill segment equals one snapshot row
- billed amount is safe at segment grain
- many bill segments have multiple determinants, so rolled-up quantity fields should not replace determinant-grain analysis

### Keep in the snapshot
- raw utility type code
- switch fields
- segment lineage IDs
- rolled-up usage and read context

### Why kept
- useful for support, audit, and exploratory context
- not all of these are intended to be headline business dimensions

## SQL Developer Debugging Steps
### Check the table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_billed_usage_rpt_curr;
```

### Inspect sample rows
```sql
SELECT *
FROM cisadm.bseg_billed_usage_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

### View the procedure text
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_BSEG_BILLED_USAGE_RPT_CURR'
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
  AND job_name = 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR';
```

### Manual refresh
```sql
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/
```

## How To Debug Common Problems
### If row counts do not match source
Check:
1. whether the base filter still uses completed bills only
2. whether duplicate `BSEG_ID` rows exist
3. whether any optional join became an inner join
4. whether the anti-join section shows missing or extra segments

### If billed amount does not match source
Check:
1. whether `CI_BSEG_CALC` is still aggregated before joining
2. whether `TOTAL_CALC_AMT` is still built from the calc aggregate
3. whether any row-multiplying join was introduced
4. whether the completed-bill filter changed

### If usage fields look strange
Check:
1. the segment's `DETERMINANT_COUNT`
2. whether the segment is multi-determinant
3. whether the user should be in the `BSEG_SQ` snapshot instead

### If determinant descriptions are missing
Check:
1. whether the segment is actually single-determinant
2. whether the corresponding lookup exists in the tenant source table
3. whether the issue is a source lookup gap instead of a snapshot defect

### If the Domain is missing fields
Check:
1. whether the column exists in Oracle
2. whether the field exists in the Domain XML
3. whether the Jaspersoft Domain was reimported after the change

## Final Status
`BSEG_BILLED_USAGE_RPT_CURR` is approved as the governed billed bill-segment snapshot.

It is:
- row-safe at `BSEG` grain
- numerically reconciled to source
- operationally refreshable
- documented for replication and debugging
- appropriate for billed amount reporting at bill-segment grain

It should not be treated as the main usage-truth layer when determinant-level usage analysis is required.
