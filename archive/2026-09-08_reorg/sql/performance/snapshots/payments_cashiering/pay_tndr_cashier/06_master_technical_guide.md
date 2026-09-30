# PAY_TNDR_CASH_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed tender-centered payments snapshot `CISADM.PAY_TNDR_CASH_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug tender, staged-source, deposit, and overlay issues
- understand the final post-QA end state without reconstructing it from multiple files

## Final End State
Object summary:
- table: `CISADM.PAY_TNDR_CASH_RPT_CURR`
- grain: one row per `PAY_TENDER_ID`
- natural key: `PAY_TENDER_ID`
- refresh procedure: `CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR`
- scheduler job: `CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR_JB`
- workspace Domain XML: `sql/performance/snapshots/payments_cashiering/pay_tndr_cashier/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `PAY_TNDR_CASH_RPT_CURR`
- refresh pattern: `DELETE + base INSERT + post-load MERGE/UPDATE enrichment + COMMIT`
- scheduler interval: daily at `06:00`
- source population: all rows in `CISADM.CI_PAY_TNDR`
- primary additive measure: `TENDER_AMT`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed payment-intake and cashiering layer at tender grain.

It answers questions like:
- which tender channels are driving payment intake
- how OriginPay compares to other sources
- what tender-control and deposit-control context exists for each tender
- which tenders are staged external tenders
- what lightweight event, customer, and pay-segment context surrounds the tender

It is intentionally a tender-grain object.

It is not for:
- raw row-per-pay-segment application detail
- debt exposure truth
- FT / GL payment accounting detail
- additive event-level or deposit-level totals summed across tender rows

## Original Design Problem
The older payments reporting estate mixed tender, pay, pay-segment, and control-table logic in ways that made grain ambiguous.

What that older approach did well:
- exposed useful payment channel context
- exposed tender and control data needed for cashiering analysis
- surfaced enough information for operational review

What was wrong or insufficient about the older approach:
1. It risked fan-out when `PAY -> PAY_SEG` detail was joined directly into a tender-centered reporting layer.
2. It did not package one governed Oracle snapshot with repeatable refresh and QA logic.
3. It blurred additive tender truth and repeated event/deposit overlays.
4. It did not provide a durable governed source-family classification for payment channels.

## What Was Corrected In The Final Snapshot
The final governed snapshot fixes those issues in these specific ways.

### 1. The grain is explicit and enforced
The final governed object is one row per `PAY_TENDER_ID`.

### 2. Tender truth is separated from repeated overlays
`TENDER_AMT` is the trusted additive measure.

Event-level pay amounts, event-level tender totals, pay-segment totals, and deposit balances are retained as contextual overlays only.

### 3. The reporting logic now lives in Oracle
The final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation SQL
- a documented QA result

### 4. Staged and external-source enrichment is applied after the base load
The base load stays at tender grain. Staged tender, customer, deposit summary, and pay-segment overlays are filled through post-load `MERGE` and `UPDATE` steps so tender grain is preserved.

### 5. Source-family classification is governed
The snapshot derives:
- `ORIGINPAY`
- `LEGACY_APAY`
- `OTHER`
- `STAGED_EXTERNAL`

This creates a stable channel grouping for reporting.

## Design Promise
The design promise is:

"For each tender in `CI_PAY_TNDR`, publish exactly one row with additive tender amount plus safe event, source, control, staged-source, customer, and pay-segment context, without changing tender grain."

That means:
- the driver is `CI_PAY_TNDR`
- one row equals one tender
- `TENDER_AMT` remains additive at snapshot grain
- repeated event and deposit values are context only

## Population Boundary
Current governed population:

```sql
FROM cisadm.ci_pay_tndr pt
```

Included population:
- all `CI_PAY_TNDR` rows

Excluded population:
- none from the base tender source

Staged-source note:
- staged tender rows in `CI_PAY_TNDR_ST` only populate the snapshot when they join to a base tender in `CI_PAY_TNDR`

## Grain And Join Safety Rules
The grain is one row per `PAY_TENDER_ID`.

This is protected by:
- driving the base load from `CI_PAY_TNDR`
- using summarized event-level subqueries for `CI_PAY`
- avoiding direct base-load fan-out through `CI_PAY_SEG`
- applying customer, staged-source, deposit-summary, and pay-segment overlays after the base load
- using one selected account-person row per payor account

This prevents:
- `PAY -> PAY_SEG` multiplication in the base insert
- customer fan-out
- staged-source enrichment from changing the tender population

## Final Refresh Procedure
The final procedure implementation is in `02_refresh_snapshot_procedure.sql`.

The final procedure behavior is:
- clear the snapshot with `DELETE`
- load the tender-grain base population from `CI_PAY_TNDR`
- attach event-level payment summary and event-level tender summary
- carry deposit-control start and end balances from `CI_DEP_CTL`
- enrich customer context through one selected account-person row
- enrich staged external-source context from `CI_PAY_TNDR_ST` and `CI_APAY_SRC`
- enrich deposit summary from `CI_TNDR_DEP`
- reclassify source family after staged-source enrichment
- enrich event-level pay-segment summary from `CI_PAY` + `CI_PAY_SEG`
- commit

## Source Family Logic
Base classification:
- `ORIGINPAY` when `TENDER_TYPE_CD IN ('OPCC','OPOC')` or `TNDR_SOURCE_CD = 'ORIGINP'`
- `LEGACY_APAY` when `TNDR_SOURCE_CD = 'ACH'`
- `OTHER` otherwise

Final classification after staged enrichment:
- `STAGED_EXTERNAL` when `STAGED_TENDER_SW = 'Y'`
- otherwise keep the governed `ORIGINPAY`, `LEGACY_APAY`, or `OTHER` rules

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB (
        job_name        => 'CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR_JB',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=6;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refreshes PAY_TNDR_CASH_RPT_CURR daily at 6:00 AM'
    );
END;
/
```

## Domain Contract
The final Domain is a single-table JDBC Domain on `PAY_TNDR_CASH_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Implementation facts:
- file name: `PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`
- top-level reporting shape: single physical table, no Domain-side join tree
- intended user view: tender, source, control, event, customer, and staged-source context in one governed layer

## Validation And QA Approach
The package validates:
- source and snapshot tender counts
- duplicate natural-key checks
- missing description coverage
- additive tender amount parity
- staged-source linkage
- tender-control and deposit-control coverage
- deposit-control start/end balance parity
- governed source-family classification

Validation file:
- `04_validation_queries.sql`

Intensive QA file:
- `07_intensive_qa_queries.sql`

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source tender count: `648,916`
- snapshot tender count: `648,916`
- count difference: `0`
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`
- source `TENDER_AMT`: `1.2579E+10`
- snapshot `TENDER_AMT`: `1.2579E+10`
- `TENDER_AMT` difference: `0`

### Description coverage
Missing rows were `0` for:
- `TENDER_TYPE_DESC`
- `TNDR_SOURCE_DESC`
- `EVENT_PAY_STATUS_DESC`
- `APAY_SRC_NAME`
- `SOURCE_FAMILY_DESC`
- `CUSTOMER_NAME`

### Staged-source and control coverage
- staged tender rows in snapshot: `1,547`
- staged tender rows joining base tender: `1,547`
- orphan staged rows not in base tender: `1`
- missing `TNDR_CTL_ID`: `0`
- missing `DEP_CTL_ID`: `0`

Interpretation:
- staged-source linkage matches the governed base tender population exactly
- the single orphan stage row exists in `CI_PAY_TNDR_ST` without a matching base tender and is not a snapshot defect

### Source-family classification
- `ACH` rows not classified `LEGACY_APAY`: `0`
- `ORIGINP` / OriginPay rows not classified `ORIGINPAY`: `0`

Derived profile:
- `ORIGINPAY`: `162,408` rows, `1.2390E+10`
- `LEGACY_APAY`: `375,155` rows, `134,005,741`
- `OTHER`: `109,806` rows, `54,520,147.6`
- `STAGED_EXTERNAL`: `1,547` rows, `435,846.22`

## Deployment Or Replication Steps
1. Run `01_create_snapshot_table.sql` in Oracle.
2. If the existing table needs the staged-source columns, run `01b_alter_existing_snapshot_table.sql`.
3. Create or replace the procedure with `02_refresh_snapshot_procedure.sql`.
4. Create the scheduler job with `03_schedule_snapshot_job.sql`.
5. Run a manual refresh:

```sql
BEGIN
    cisadm.refresh_pay_tndr_cash_rpt_curr;
END;
/
```

6. Run `04_validation_queries.sql`.
7. Import or reimport `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml`.

## Debugging Guidance
Use SQL Developer to inspect the current state:

```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.pay_tndr_cash_rpt_curr;
```

```sql
SELECT *
FROM cisadm.pay_tndr_cash_rpt_curr
WHERE staged_tender_sw = 'Y'
   OR ext_source_id IS NOT NULL
FETCH FIRST 10 ROWS ONLY;
```

```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_PAY_TNDR_CASH_RPT_CURR'
  AND type = 'PROCEDURE'
ORDER BY line;
```

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No`
- Needs population change: `No`
- Keep overlay caveats documented: `Yes`
