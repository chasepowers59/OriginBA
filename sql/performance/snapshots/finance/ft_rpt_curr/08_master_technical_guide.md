# FT_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed FT header snapshot `CISADM.FT_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- see what changed from the original financial transaction domain reference
- recreate the table, procedure, and scheduler job
- validate the data against the database
- debug population, lookup, and refresh issues
- understand the final post-QA end state without having to reconstruct the history from multiple files

## Final End State
Object summary:
- table: `CISADM.FT_RPT_CURR`
- grain: one row per `CI_FT.FT_ID`
- refresh procedure: `CISADM.REFRESH_FT_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_FT_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/finance/ft_rpt_curr/FT_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/FT_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `FT_RPT_CURR`
- refresh pattern: `TRUNCATE + INSERT + COMMIT`
- scheduler interval: every 6 hours at `01:00`, `07:00`, `13:00`, and `19:00 GMT`
- primary additive measure: `CUR_AMT`
- secondary amount carried for payoff-oriented analysis: `TOT_AMT`
- source population: all non-redundant FT rows where `CI_FT.REDUNDANT_SW = 'N'`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed FT header reporting layer for finance.

It answers questions like:
- how many financial transactions occurred
- how much FT dollar volume exists
- what FT types are driving that volume
- which accounts and service agreements those transactions belong to
- which transactions tie to bill segments, adjustments, or payment segments
- what the current GL distribution status is at FT header grain

It is intentionally not a GL-line snapshot.

It is not for:
- GL account analysis
- distribution-code analysis
- row-per-`CI_FT_GL` reconciliation

Those belong in `FT_GL_DISTRIBUTION_RPT_CURR`.

## Original Financial Transaction Domain Reference
The original reference state was not a single governed FT-header snapshot. It was a Jasper-side finance/domain lineage where FT fields were exposed through manual Domain XML and BI views rather than through one governed Oracle table.

The main legacy reference patterns used for FT information were:
- `domains/working/manual_designs/Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml`
  This exposed FT fields from `C1_BI_FT_VW` inside a usage-billing-finance bridge domain.
- `domains/working/manual_designs/Usage_Billing_Financial_Bridge_PerfFast_6M.xml`
  This exposed pre-aggregated FT measures in a bridge design rather than a reusable FT-header object.
- `domains/working/manual_designs/Fund_Balance_Final_DB_Validated.xml`
  This exposed `CI_FT` together with `CI_FT_GL` and related finance objects for GL analysis, not for one-row-per-FT header reporting.

Those artifacts were useful references for field naming and finance subject matter, but they were not the right end state for a governed FT header snapshot.

What that original domain/reference did well:
- started from the correct finance fact family, `CI_FT`
- exposed core FT header fields
- exposed linked context such as SA, bill segment, adjustment, and payment references
- provided business-facing labels for some status/type fields

What was wrong or insufficient about the original domain/reference for governed reporting:
1. The business logic lived in the Domain layer instead of in Oracle.
   That meant the semantic contract was not persisted as a governed database object.
2. There was no controlled refresh object.
   There was no single governed table plus procedure plus scheduler pattern that another person could inspect and rerun reliably.
3. Validation was not packaged as a repeatable DB-side QA process.
   It was possible to use the domain without a formal, reusable source-to-snapshot parity pack.
4. The legacy reference mixed subject areas.
   FT fields appeared inside broader bridge or GL-oriented domains, which made it too easy to answer FT-header questions from objects that were actually designed for different grains or different business promises.
5. Some account-context fields that business users care about were not fully business-ready in the governed contract.
   The final governed snapshot now carries both code and description for customer class, collection class, bill cycle, and account management group.
6. The old reference was presentation-first, not operationally supportable.
   Someone debugging later needed exact DB objects, exact SQL, exact validation steps, exact scheduler checks, and exact numeric evidence. That did not exist as a single technical artifact.

## What We Changed From The Original Domain Reference
The final governed FT snapshot changed the old reference approach in these specific ways.

### 0. We replaced a domain lineage with a governed FT-header artifact
Legacy reference shape:
- Jasper manual domains reading FT-related data from `C1_BI_FT_VW` or mixed `CI_FT`/`CI_FT_GL` join trees
- no single FT-header Oracle snapshot object
- no single FT-header importable Domain intended to be the stable end-user entry point

Final governed shape:
- Oracle table `CISADM.FT_RPT_CURR`
- stored procedure `CISADM.REFRESH_FT_RPT_CURR`
- scheduler job `CISADM.JOB_REFRESH_FT_RPT_CURR`
- single-table importable Domain XML `FT_RPT_CURR_End_User_Friendly.xml`

Why this matters:
- the FT header subject is now its own governed reporting product
- users no longer need to borrow FT fields from broader bridge or GL domains
- support staff can inspect one object family instead of reverse-engineering multiple older manual designs

### 1. We moved the reporting logic into Oracle
Instead of relying on the Jasper domain to be the main semantic implementation, we created:
- a physical table
- a stored refresh procedure
- a scheduler job
- repeatable validation and intensive QA SQL

Why this matters:
- Oracle now owns the row grain and business context logic
- Jasper only reads the governed result
- support and debugging no longer depend on reverse-engineering a Domain join tree

### 2. We fixed the business-readiness gap for account context
The final governed table now includes both code and description for:
- `CUST_CL_CD` and `CUST_CL_DESC`
- `COLL_CL_CD` and `COLL_CL_DESC`
- `BILL_CYC_CD` and `BILL_CYC_DESC`
- `ACCT_MGMT_GRP_CD` and `ACCT_MGMT_GRP_DESC`

Why this matters:
- business users can group and filter on readable labels
- technical users still have the raw codes
- the object works better for ad hoc analysis without losing traceability

### 3. We made the FT grain explicit and supportable
The final governed object states and enforces:
- one row per `FT_ID`
- no `CI_FT_GL` join
- no mixed FT header / GL detail grain
- child overlays only when the FT family makes sense

Why this matters:
- sums and counts are stable
- users know exactly what one row represents
- finance header reporting does not get contaminated by GL detail fanout

What was wrong in the legacy reference:
- the older finance reference estate included domains where FT and FT GL subjects were presented together
- that was valid for GL analysis, but it was the wrong foundation for a reusable FT-header domain because one FT can have multiple GL lines
- the final snapshot fixes that by refusing to join `CI_FT_GL` at all

### 4. We created an operational refresh model
The final object has:
- a named procedure
- a named scheduler job
- a defined cadence
- exact SQL Developer inspection steps

Why this matters:
- another person can see how it refreshes
- another person can run it manually
- another person can confirm whether it failed, ran, or needs to be disabled

What was wrong in the legacy reference:
- the old domain XML told Jasper what to read, but it did not define a DBA-visible refresh contract
- the final snapshot fixes that by giving operations a real table refresh lifecycle in Oracle

### 5. We created a repeatable QA evidence pack
The final state includes:
- fast validation SQL
- intensive source-vs-snapshot QA SQL
- documented results with exact counts and totals

Why this matters:
- the object is not trusted just because it exists
- it is trusted because it was reconciled back to `CI_FT`

### 6. We corrected the end-user field contract
The old reference estate did not give FT-header users a single clean contract where the most important utility-facing classifications were consistently exposed as both code and readable description.

The final end-user Domain contract now explicitly carries:
- `FT_TYPE_FLG` and `FT_TYPE_FLG_DESC`
- `GL_DISTRIB_STATUS` and `GL_DISTRIB_STATUS_DESC`
- `SA_STATUS_FLG` and `SA_STATUS_DESC`
- `SA_TYPE_CD` and `SA_TYPE_DESC`
- `CUST_CL_CD` and `CUST_CL_DESC`
- `COLL_CL_CD` and `COLL_CL_DESC`
- `BILL_CYC_CD` and `BILL_CYC_DESC`
- `ACCT_MGMT_GRP_CD` and `ACCT_MGMT_GRP_DESC`

What was wrong in the legacy reference:
- some of these business-friendly descriptions either were not part of a single governed FT contract or were only implied by Jasper-side design
- the final snapshot fixes that by persisting the descriptive context in Oracle itself

## Design Promise
The design promise is:

"For each non-redundant financial transaction, publish exactly one row with safe FT-header context and optional FT-type-specific child detail, without changing the FT grain."

That means:
- base population comes from `CI_FT`
- only `REDUNDANT_SW = 'N'` rows are included
- bill segment, adjustment, and payment details are overlays, not separate row drivers
- the object is not a GL-line fact

## Population Boundary
Current governed population:
```sql
WHERE ft.redundant_sw = 'N'
```

Included FT families validated in QA:
- `AD`
- `AX`
- `BS`
- `BX`
- `PS`
- `PX`

Why this boundary was chosen:
- this is a finance header snapshot, so it should represent the full non-redundant FT population
- narrowing it further would turn it into a subject-specific FT subset instead of the shared FT header layer

## Grain And Join Safety Rules
The grain is one row per `FT_ID`.

This is protected by:
- driving from `CI_FT`
- never joining to `CI_FT_GL`
- using `LEFT JOIN`s for optional context
- gating child joins by FT family

Child-overlay rules:
- `BS`, `BX` populate bill-segment fields
- `AD`, `AX` populate adjustment fields
- `PS`, `PX` populate payment-segment fields

This prevents:
- row multiplication from unrelated child tables
- accidental loss of FT rows from inner joins to optional children
- mixed-grain reporting

## Final Table Contract
The final table DDL is:

```sql
CREATE TABLE cisadm.ft_rpt_curr (
    ft_id                  VARCHAR2(30)    NOT NULL,
    ft_type_flg            VARCHAR2(5),
    ft_type_flg_desc       VARCHAR2(60),
    accounting_dt          DATE,
    cre_dttm               TIMESTAMP,
    freeze_dttm            TIMESTAMP,
    freeze_user_id         VARCHAR2(30),
    freeze_user_name       VARCHAR2(200),
    cur_amt                NUMBER(15,2),
    tot_amt                NUMBER(15,2),
    currency_cd            VARCHAR2(10),
    bill_id                VARCHAR2(30),
    sa_id                  VARCHAR2(30),
    parent_id              VARCHAR2(30),
    sibling_id             VARCHAR2(30),
    gl_distrib_status      VARCHAR2(5),
    gl_distrib_status_desc VARCHAR2(60),
    acct_id                VARCHAR2(30),
    load_dttm              TIMESTAMP DEFAULT SYSTIMESTAMP,
    sa_status_flg          VARCHAR2(10),
    sa_status_desc         VARCHAR2(100),
    sa_type_cd             VARCHAR2(10),
    sa_type_desc           VARCHAR2(100),
    cust_cl_cd             VARCHAR2(10),
    cust_cl_desc           VARCHAR2(100),
    coll_cl_cd             VARCHAR2(10),
    coll_cl_desc           VARCHAR2(100),
    bill_cyc_cd            VARCHAR2(10),
    bill_cyc_desc          VARCHAR2(100),
    acct_mgmt_grp_cd       VARCHAR2(10),
    acct_mgmt_grp_desc     VARCHAR2(100),
    bseg_id                VARCHAR2(30),
    bseg_stat_flg          VARCHAR2(10),
    bseg_stat_desc         VARCHAR2(100),
    start_dt               DATE,
    end_dt                 DATE,
    adj_id                 VARCHAR2(30),
    adj_status_flg         VARCHAR2(10),
    adj_status_desc        VARCHAR2(100),
    adj_type_cd            VARCHAR2(10),
    adj_type_desc          VARCHAR2(100),
    adj_amt                NUMBER(15,2),
    pay_seg_id             VARCHAR2(30),
    pay_id                 VARCHAR2(30),
    pay_seg_amt            NUMBER(15,2)
);
```

## Existing-Table Upgrade DDL
If the earlier deployed table exists and needs to be brought to the final post-QA column contract, use:

```sql
ALTER TABLE cisadm.ft_rpt_curr ADD (
    cust_cl_desc       VARCHAR2(100),
    coll_cl_desc       VARCHAR2(100),
    bill_cyc_desc      VARCHAR2(100),
    acct_mgmt_grp_desc VARCHAR2(100)
);
```

## Field Inventory With Meaning
### Core FT fields
- `FT_ID`: natural key, one row per financial transaction
- `FT_TYPE_FLG`: raw FT type code
- `FT_TYPE_FLG_DESC`: business label for FT type
- `ACCOUNTING_DT`: accounting date
- `CRE_DTTM`: FT create timestamp
- `FREEZE_DTTM`: freeze timestamp
- `FREEZE_USER_ID`: raw freezing user
- `FREEZE_USER_NAME`: business-friendly freezing user name
- `CUR_AMT`: primary additive FT amount
- `TOT_AMT`: payoff-oriented FT amount
- `CURRENCY_CD`: source currency code
- `BILL_ID`: linked bill header when present
- `SA_ID`: linked service agreement
- `PARENT_ID`: source parent reference
- `SIBLING_ID`: source sibling reference
- `GL_DISTRIB_STATUS`: raw GL distribution status code
- `GL_DISTRIB_STATUS_DESC`: decoded GL distribution status
- `ACCT_ID`: linked account
- `LOAD_DTTM`: snapshot load timestamp

### Service agreement and account context
- `SA_STATUS_FLG`: raw SA status
- `SA_STATUS_DESC`: SA status description
- `SA_TYPE_CD`: raw SA type
- `SA_TYPE_DESC`: SA type description, used as service type
- `CUST_CL_CD`: raw customer class
- `CUST_CL_DESC`: customer class description
- `COLL_CL_CD`: raw collection class
- `COLL_CL_DESC`: collection class description
- `BILL_CYC_CD`: raw bill cycle
- `BILL_CYC_DESC`: bill cycle description
- `ACCT_MGMT_GRP_CD`: raw account management group
- `ACCT_MGMT_GRP_DESC`: account management group description when available in tenant lookup data

### Bill segment context
- `BSEG_ID`: linked bill segment for FT families `BS` and `BX`
- `BSEG_STAT_FLG`: raw bill segment status
- `BSEG_STAT_DESC`: bill segment status description
- `START_DT`: bill segment start date
- `END_DT`: bill segment end date

### Adjustment context
- `ADJ_ID`: linked adjustment for FT families `AD` and `AX`
- `ADJ_STATUS_FLG`: raw adjustment status
- `ADJ_STATUS_DESC`: adjustment status description
- `ADJ_TYPE_CD`: raw adjustment type
- `ADJ_TYPE_DESC`: adjustment type description
- `ADJ_AMT`: adjustment amount from `CI_ADJ`

### Payment context
- `PAY_SEG_ID`: linked payment segment for FT families `PS` and `PX`
- `PAY_ID`: linked payment header
- `PAY_SEG_AMT`: pay segment amount

## Final Refresh Procedure
The final procedure definition is:

```sql
CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.ft_rpt_curr';

    INSERT INTO cisadm.ft_rpt_curr (
        ft_id,
        ft_type_flg,
        ft_type_flg_desc,
        accounting_dt,
        cre_dttm,
        freeze_dttm,
        freeze_user_id,
        freeze_user_name,
        cur_amt,
        tot_amt,
        currency_cd,
        bill_id,
        sa_id,
        parent_id,
        sibling_id,
        gl_distrib_status,
        gl_distrib_status_desc,
        acct_id,
        load_dttm,
        sa_status_flg,
        sa_status_desc,
        sa_type_cd,
        sa_type_desc,
        cust_cl_cd,
        cust_cl_desc,
        coll_cl_cd,
        coll_cl_desc,
        bill_cyc_cd,
        bill_cyc_desc,
        acct_mgmt_grp_cd,
        acct_mgmt_grp_desc,
        bseg_id,
        bseg_stat_flg,
        bseg_stat_desc,
        start_dt,
        end_dt,
        adj_id,
        adj_status_flg,
        adj_status_desc,
        adj_type_cd,
        adj_type_desc,
        adj_amt,
        pay_seg_id,
        pay_id,
        pay_seg_amt
    )
    SELECT
        ft.ft_id,
        ft.ft_type_flg,
        CASE ft.ft_type_flg
            WHEN 'AD' THEN 'Adjustment'
            WHEN 'AX' THEN 'Adjustment Cancellation'
            WHEN 'BS' THEN 'Bill Segment'
            WHEN 'BX' THEN 'Bill Segment Cancellation'
            WHEN 'PS' THEN 'Pay Segment'
            WHEN 'PX' THEN 'Pay Segment Cancellation'
        END AS ft_type_flg_desc,
        ft.accounting_dt,
        ft.cre_dttm,
        ft.freeze_dttm,
        ft.freeze_user_id,
        COALESCE(NULLIF(TRIM(u.first_name || ' ' || u.last_name), ''), u.user_id) AS freeze_user_name,
        ft.cur_amt,
        ft.tot_amt,
        ft.currency_cd,
        ft.bill_id,
        ft.sa_id,
        ft.parent_id,
        ft.sibling_id,
        ft.gl_distrib_status,
        CASE ft.gl_distrib_status
            WHEN 'D' THEN 'Distributed'
            WHEN 'G' THEN 'Generated'
            WHEN 'M' THEN 'Modified'
            WHEN 'N' THEN 'Pending'
        END AS gl_distrib_status_desc,
        sa.acct_id,
        SYSTIMESTAMP,
        sa.sa_status_flg,
        sa_stat.descr        AS sa_status_desc,
        sa.sa_type_cd,
        sa_type.descr        AS sa_type_desc,
        acct.cust_cl_cd,
        cust_cl_l.descr      AS cust_cl_desc,
        acct.coll_cl_cd,
        coll_cl_l.descr      AS coll_cl_desc,
        acct.bill_cyc_cd,
        bill_cyc_l.descr     AS bill_cyc_desc,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr    AS acct_mgmt_grp_desc,
        bseg.bseg_id,
        bseg.bseg_stat_flg,
        bseg_stat.descr      AS bseg_stat_desc,
        bseg.start_dt,
        bseg.end_dt,
        adj.adj_id,
        adj.adj_status_flg,
        adj_stat.descr       AS adj_status_desc,
        adj.adj_type_cd,
        adj_type.descr       AS adj_type_desc,
        adj.adj_amt,
        pay.pay_seg_id,
        pay.pay_id,
        pay.pay_seg_amt
    FROM cisadm.ci_ft ft
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN cisadm.sc_user u
        ON u.user_id = ft.freeze_user_id
       AND u.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay
        ON pay.pay_seg_id = ft.sibling_id
       AND pay.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    LEFT JOIN cisadm.ci_lookup_val_l sa_stat
        ON sa_stat.field_name  = 'SA_STATUS_FLG'
       AND sa_stat.field_value = sa.sa_status_flg
       AND sa_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type
        ON sa_type.sa_type_cd  = sa.sa_type_cd
       AND sa_type.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l bill_cyc_l
        ON bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_stat
        ON bseg_stat.field_name  = 'BSEG_STAT_FLG'
       AND bseg_stat.field_value = bseg.bseg_stat_flg
       AND bseg_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l adj_stat
        ON adj_stat.field_name  = 'ADJ_STATUS_FLG'
       AND adj_stat.field_value = adj.adj_status_flg
       AND adj_stat.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_adj_type_l adj_type
        ON adj_type.adj_type_cd  = adj.adj_type_cd
       AND adj_type.language_cd  = 'ENG'
    WHERE ft.redundant_sw = 'N';

    COMMIT;
END;
/
```

## Why The Final Procedure Looks This Way
Specific final design decisions:
- `TRUNCATE` was kept because the user accepted a short empty-window refresh and wanted the simpler, faster table refresh pattern
- `LOAD_DTTM` is populated as `SYSTIMESTAMP` at refresh time
- `COALESCE(NULLIF(TRIM(first_name || ' ' || last_name), ''), user_id)` was kept for `FREEZE_USER_NAME` so the field is usable even when the person name is blank
- child joins remain gated by FT family to keep the FT grain stable
- business-ready descriptions are embedded in the refresh so Jasper does not need to rebuild them

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=1,7,13,19;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh FT header snapshot every 6 hours at 01:00, 07:00, 13:00, and 19:00 GMT'
    );
END;
/
```

Operational meaning:
- first eligible run is the next `01:00`, `07:00`, `13:00`, or `19:00 GMT` scheduler slot after creation
- then runs every 6 hours at `01:00`, `07:00`, `13:00`, and `19:00 GMT`
- because the pattern is full rebuild, users should avoid querying during the refresh window if empty-table exposure matters

## Domain Contract
The final Domain is a single-table JDBC Domain on `FT_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Exact final XML implementation facts:
- file name: `FT_RPT_CURR_End_User_Friendly.xml`
- top item group id: `FT_RPT_CURR`
- top label: `Financial Transactions`
- physical source block: `<jdbcTable id="FT_RPT_CURR" datasourceId="Origin_DEV_DS" datasourceTableName="FT_RPT_CURR" schemaAlias="CISADM">`
- design approach: single physical table, no Domain-side join tree
- reason: preserve FT grain in Oracle and keep Jasper consumption simple

This is materially different from the legacy finance reference designs, which exposed FT information through manual-domain queries or broader join trees. The final governed Domain does not need Jasper to recreate FT logic. Jasper only reads the finished FT snapshot.

Final item groups exposed:
- `FT_CORE`
- `FT_SA_ACCT`
- `FT_BSEG`
- `FT_ADJ`
- `FT_PAYMENT`

Final user-facing field list by group:

`FT_CORE`
- `FT_ID`
- `FT_TYPE_FLG_DESC`
- `FT_TYPE_FLG`
- `CUR_AMT`
- `TOT_AMT`
- `CURRENCY_CD`
- `ACCOUNTING_DT`
- `CRE_DTTM`
- `FREEZE_DTTM`
- `FREEZE_USER_NAME`
- `FREEZE_USER_ID`
- `GL_DISTRIB_STATUS_DESC`
- `GL_DISTRIB_STATUS`
- `BILL_ID`
- `PARENT_ID`
- `SIBLING_ID`
- `LOAD_DTTM`

`FT_SA_ACCT`
- `ACCT_ID`
- `SA_ID`
- `SA_STATUS_DESC`
- `SA_STATUS_FLG`
- `SA_TYPE_DESC`
- `SA_TYPE_CD`
- `CUST_CL_DESC`
- `CUST_CL_CD`
- `COLL_CL_DESC`
- `COLL_CL_CD`
- `BILL_CYC_DESC`
- `BILL_CYC_CD`
- `ACCT_MGMT_GRP_DESC`
- `ACCT_MGMT_GRP_CD`

`FT_BSEG`
- `BSEG_ID`
- `BSEG_STAT_DESC`
- `BSEG_STAT_FLG`
- `START_DT`
- `END_DT`

`FT_ADJ`
- `ADJ_ID`
- `ADJ_TYPE_DESC`
- `ADJ_TYPE_CD`
- `ADJ_STATUS_DESC`
- `ADJ_STATUS_FLG`
- `ADJ_AMT`

`FT_PAYMENT`
- `PAY_SEG_ID`
- `PAY_ID`
- `PAY_SEG_AMT`

Legacy-to-final Domain change summary:
- old reference state: FT content was embedded inside broader finance or bridge domains
- final state: FT has its own importable single-table Domain
- old reference state: domain-level design was part of the business logic
- final state: domain-level design is only a presentation layer over governed Oracle output
- old reference state: no single, supportable FT-header entry point for ad hoc
- final state: `FT_RPT_CURR` is the entry point

## Why These Domain Fields Were Exposed
Final exposure logic:
- both code and description were kept for major business dimensions so business users can read the label and analysts can still trace exact source codes
- GL-line fields were excluded entirely because this object is FT-header-only
- business-critical account/SA context was included because utilities often analyze finance data by service type, customer class, collection class, and bill cycle

## Step-By-Step Replication
### Build from scratch
1. Create the table using the full DDL shown above.
2. If needed, widen ID columns before rollout if source keys exceed `VARCHAR2(30)`.
3. Create the procedure using the full procedure definition shown above.
4. Run the manual refresh:

```sql
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/
```

5. Run the validation queries listed in the next section.
6. If validation and QA pass, create the scheduler job.
7. Publish the Domain XML using the final field contract shown above.

### Upgrade an existing earlier FT_RPT_CURR table
1. Run the alter statement shown above to add the final business description columns if they are missing.
2. Replace the procedure with the final procedure definition.
3. Refresh the table manually.
4. Re-run validation and QA.
5. Reimport or republish the Domain if the exposed field set changed.

## Validation SQL To Run
Run these in order after a manual refresh.

### Manual refresh
```sql
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/
```

### Snapshot row count
```sql
SELECT COUNT(*) AS snapshot_row_count
FROM cisadm.ft_rpt_curr;
```

### Duplicate natural-key check
```sql
SELECT
    ft_id,
    COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr
GROUP BY ft_id
HAVING COUNT(*) > 1;
```

### Null key check
```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_id IS NULL THEN 1 ELSE 0 END) AS null_ft_id_rows,
    SUM(CASE WHEN ft_type_flg IS NULL THEN 1 ELSE 0 END) AS null_ft_type_rows,
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END) AS null_acct_id_rows,
    SUM(CASE WHEN sa_id IS NULL THEN 1 ELSE 0 END) AS null_sa_id_rows
FROM cisadm.ft_rpt_curr;
```

### Description coverage check
```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_type_flg_desc IS NULL AND ft_type_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_ft_type_desc,
    SUM(CASE WHEN gl_distrib_status_desc IS NULL AND gl_distrib_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_gl_status_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN bseg_stat_desc IS NULL AND bseg_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_status_desc,
    SUM(CASE WHEN adj_status_desc IS NULL AND adj_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_status_desc,
    SUM(CASE WHEN adj_type_desc IS NULL AND adj_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_adj_type_desc
FROM cisadm.ft_rpt_curr;
```

### FT type profile
```sql
SELECT
    ft_type_flg,
    ft_type_flg_desc,
    COUNT(*) AS ft_count,
    SUM(NVL(cur_amt, 0)) AS total_cur_amt,
    SUM(NVL(tot_amt, 0)) AS total_tot_amt
FROM cisadm.ft_rpt_curr
GROUP BY ft_type_flg, ft_type_flg_desc
ORDER BY ft_type_flg;
```

### Optional child coverage by FT type
```sql
SELECT
    ft_type_flg,
    COUNT(*) AS ft_rows,
    SUM(CASE WHEN bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_bseg,
    SUM(CASE WHEN adj_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_adj,
    SUM(CASE WHEN pay_seg_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_pay_seg
FROM cisadm.ft_rpt_curr
GROUP BY ft_type_flg
ORDER BY ft_type_flg;
```

### Bill-segment date sanity
```sql
SELECT
    COUNT(*) AS rows_with_bseg_dates,
    SUM(CASE WHEN start_dt IS NOT NULL AND end_dt IS NOT NULL AND start_dt > end_dt THEN 1 ELSE 0 END) AS invalid_bseg_date_ranges
FROM cisadm.ft_rpt_curr
WHERE bseg_id IS NOT NULL;
```

### Freeze-date sanity
```sql
SELECT
    COUNT(*) AS rows_with_freeze_dttm,
    SUM(CASE WHEN cre_dttm IS NOT NULL AND freeze_dttm IS NOT NULL AND freeze_dttm < cre_dttm THEN 1 ELSE 0 END) AS freeze_before_create_rows
FROM cisadm.ft_rpt_curr
WHERE freeze_dttm IS NOT NULL;
```

## Intensive QA SQL To Run
Run these after the validation layer.

### Source vs snapshot baseline
```sql
SELECT
    (SELECT COUNT(*) FROM cisadm.ci_ft ft WHERE ft.redundant_sw = 'N') AS source_ft_count,
    (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) AS snapshot_ft_count,
    (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) -
    (SELECT COUNT(*) FROM cisadm.ci_ft ft WHERE ft.redundant_sw = 'N') AS snapshot_minus_source
FROM dual;
```

### Anti-joins
```sql
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT ft.ft_id
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
    MINUS
    SELECT s.ft_id
    FROM cisadm.ft_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.ft_id
    FROM cisadm.ft_rpt_curr s
    MINUS
    SELECT ft.ft_id
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
);
```

### Overall amount parity
```sql
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        SUM(NVL(ft.cur_amt, 0)) AS src_cur_amt,
        SUM(NVL(ft.tot_amt, 0)) AS src_tot_amt
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.cur_amt, 0)) AS snap_cur_amt,
        SUM(NVL(s.tot_amt, 0)) AS snap_tot_amt
    FROM cisadm.ft_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_cur_amt,
    snap.snap_cur_amt,
    snap.snap_cur_amt - src.src_cur_amt AS cur_amt_diff,
    src.src_tot_amt,
    snap.snap_tot_amt,
    snap.snap_tot_amt - src.src_tot_amt AS tot_amt_diff
FROM src
CROSS JOIN snap;
```

### Key identifier mismatch test
```sql
WITH paired AS (
    SELECT
        ft.ft_id,
        sa.acct_id AS src_acct_id,
        bseg.bseg_id AS src_bseg_id,
        adj.adj_id AS src_adj_id,
        pay.pay_seg_id AS src_pay_seg_id,
        s.acct_id AS snap_acct_id,
        s.bseg_id AS snap_bseg_id,
        s.adj_id AS snap_adj_id,
        s.pay_seg_id AS snap_pay_seg_id
    FROM cisadm.ci_ft ft
    INNER JOIN cisadm.ft_rpt_curr s
        ON s.ft_id = ft.ft_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay
        ON pay.pay_seg_id = ft.sibling_id
       AND pay.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    WHERE ft.redundant_sw = 'N'
)
SELECT
    SUM(CASE WHEN NVL(src_acct_id, '#NULL#') <> NVL(snap_acct_id, '#NULL#') THEN 1 ELSE 0 END) AS acct_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_bseg_id, '#NULL#') <> NVL(snap_bseg_id, '#NULL#') THEN 1 ELSE 0 END) AS bseg_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_adj_id, '#NULL#') <> NVL(snap_adj_id, '#NULL#') THEN 1 ELSE 0 END) AS adj_id_mismatch_rows,
    SUM(CASE WHEN NVL(src_pay_seg_id, '#NULL#') <> NVL(snap_pay_seg_id, '#NULL#') THEN 1 ELSE 0 END) AS pay_seg_id_mismatch_rows
FROM paired;
```

### Business-context lookup availability
```sql
WITH cust_cl_codes AS (
    SELECT DISTINCT s.cust_cl_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.cust_cl_cd IS NOT NULL
),
coll_cl_codes AS (
    SELECT DISTINCT s.coll_cl_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.coll_cl_cd IS NOT NULL
),
bill_cyc_codes AS (
    SELECT DISTINCT s.bill_cyc_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.bill_cyc_cd IS NOT NULL
),
acct_mgmt_codes AS (
    SELECT DISTINCT s.acct_mgmt_grp_cd AS code FROM cisadm.ft_rpt_curr s WHERE s.acct_mgmt_grp_cd IS NOT NULL
)
SELECT
    'CUST_CL_CD' AS code_column,
    COUNT(*) AS distinct_code_count,
    SUM(CASE WHEN l.cust_cl_cd IS NULL THEN 1 ELSE 0 END) AS codes_missing_lookup
FROM cust_cl_codes c
LEFT JOIN cisadm.ci_cust_cl_l l
    ON l.cust_cl_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'COLL_CL_CD',
    COUNT(*),
    SUM(CASE WHEN l.coll_cl_cd IS NULL THEN 1 ELSE 0 END)
FROM coll_cl_codes c
LEFT JOIN cisadm.ci_coll_cl_l l
    ON l.coll_cl_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'BILL_CYC_CD',
    COUNT(*),
    SUM(CASE WHEN l.bill_cyc_cd IS NULL THEN 1 ELSE 0 END)
FROM bill_cyc_codes c
LEFT JOIN cisadm.ci_bill_cyc_l l
    ON l.bill_cyc_cd = c.code
   AND l.language_cd = 'ENG'
UNION ALL
SELECT
    'ACCT_MGMT_GRP_CD',
    COUNT(*),
    SUM(CASE WHEN l.acct_mgmt_grp_cd IS NULL THEN 1 ELSE 0 END)
FROM acct_mgmt_codes c
LEFT JOIN cisadm.ci_acct_mgmt_gr_l l
    ON l.acct_mgmt_grp_cd = c.code
   AND l.language_cd = 'ENG';
```

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source FT count: `4,856,123`
- snapshot FT count: `4,856,123`
- count difference: `0`
- source `CUR_AMT`: `3,009,107.78`
- snapshot `CUR_AMT`: `3,009,107.78`
- `CUR_AMT` difference: `0`
- source `TOT_AMT`: `3,682,478.38`
- snapshot `TOT_AMT`: `3,682,478.38`
- `TOT_AMT` difference: `0`

### Anti-joins and key safety
- source rows missing in snapshot: `0`
- snapshot rows not in source: `0`
- duplicate `FT_ID` rows: `0`
- `ACCT_ID` mismatch rows: `0`
- `BSEG_ID` mismatch rows: `0`
- `ADJ_ID` mismatch rows: `0`
- `PAY_SEG_ID` mismatch rows: `0`

### FT-family parity
All six FT families matched exactly for:
- row counts
- `CUR_AMT`
- `TOT_AMT`

Validated families:
- `AD`
- `AX`
- `BS`
- `BX`
- `PS`
- `PX`

### Description parity
Mismatch counts were all `0` for:
- FT type description
- GL distribution status description
- SA status description
- SA type description
- customer class description
- collection class description
- bill cycle description where source lookup exists
- account management group description where source lookup exists
- bill segment status description
- adjustment status description
- adjustment type description
- freeze user name

### Remaining source lookup gaps
These are source-data coverage gaps, not snapshot logic defects:
- `SA_TYPE_CD`: `26`
- `ADJ_TYPE_CD`: `35`
- `BILL_CYC_CD`: `675`
- `ACCT_MGMT_GRP_CD`: one distinct code present with no maintained lookup translation

### Data anomaly still present in source
- `3` rows where `FREEZE_DTTM < CRE_DTTM`

Interpretation:
- treat as source-data anomaly unless business requires investigation

## Final Decisions On Business Context
### Kept in the snapshot
- raw codes and descriptions for customer class, collection class, bill cycle, and account management group
- child IDs for traceability
- user and audit timestamps

### Why kept
- ad hoc users need readable business labels
- analysts still need raw codes for debugging and reconciliation
- traceability matters in finance support

### Account management group decision
Final decision:
- keep `ACCT_MGMT_GRP_CD` and `ACCT_MGMT_GRP_DESC` in the snapshot
- do not invent or hardcode a translation
- document that the tenant lookup is not maintained

## SQL Developer Debugging Steps
### Check the table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.ft_rpt_curr;
```

### Inspect sample rows
```sql
SELECT *
FROM cisadm.ft_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

### View the procedure text
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_FT_RPT_CURR'
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
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR';
```

### View recent scheduler history
```sql
SELECT log_id,
       job_name,
       status,
       actual_start_date,
       run_duration,
       additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name = 'JOB_REFRESH_FT_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

### Disable the job
```sql
BEGIN
    DBMS_SCHEDULER.DISABLE('CISADM.JOB_REFRESH_FT_RPT_CURR');
END;
/
```

### Re-enable the job
```sql
BEGIN
    DBMS_SCHEDULER.ENABLE('CISADM.JOB_REFRESH_FT_RPT_CURR');
END;
/
```

### Manual refresh
```sql
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/
```

## How To Debug Common Problems
### If row counts do not match source
Check:
1. whether the base filter still uses `REDUNDANT_SW = 'N'`
2. whether someone changed a `LEFT JOIN` to an `INNER JOIN`
3. whether a child join lost its FT-family gate
4. whether rows are missing in anti-join results

### If amounts do not match source
Check:
1. whether duplicate `FT_ID` rows exist
2. whether someone added a join that multiplies rows
3. whether the wrong source table was introduced
4. whether `CUR_AMT` or `TOT_AMT` was replaced with derived logic

### If bill-segment, adjustment, or payment fields look wrong
Check:
1. the FT family of the row
2. whether the child join still includes the FT-family filter
3. whether `PARENT_ID` and `SIBLING_ID` are still mapped correctly

### If descriptions are missing
Check:
1. whether the desc column exists in the table
2. whether the procedure still selects it
3. whether the lookup row exists in the tenant source table
4. whether the issue is a lookup gap or a snapshot defect

### If the Domain is missing fields
Check:
1. whether the column exists in Oracle
2. whether the field exists in the Domain XML
3. whether the Jaspersoft Domain was reimported after the change

## Final Status
`FT_RPT_CURR` is approved as the governed FT header snapshot.

It is:
- row-safe at FT grain
- numerically reconciled to source
- operationally refreshable
- documented for replication and debugging
- acceptable for ad hoc and reporting use

The remaining open issues are tenant lookup-maintenance issues, not blockers to using the snapshot.
