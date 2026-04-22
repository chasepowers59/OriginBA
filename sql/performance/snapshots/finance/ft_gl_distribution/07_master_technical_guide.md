# FT_GL_DISTRIBUTION_RPT_CURR Master Technical Guide

## Purpose
This document is the single technical source of truth for the governed FT GL distribution snapshot `CISADM.FT_GL_DISTRIBUTION_RPT_CURR`.

It is written so another analyst, developer, or support resource can:
- understand exactly what the object is
- understand why the design was chosen
- understand what was wrong with the original FT / GL domain approach
- recreate the table, procedure, scheduler job, and Domain
- validate the data against Oracle source tables
- debug row-count, amount, lookup, and refresh issues
- understand the final post-QA end state without reconstructing history from multiple artifacts

## Final End State
Object summary:
- table: `CISADM.FT_GL_DISTRIBUTION_RPT_CURR`
- grain: one row per `CI_FT_GL` line
- natural key: `FT_ID`, `GL_SEQ_NBR`
- refresh procedure: `CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`
- scheduler job: `CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR`
- workspace Domain XML: `sql/performance/snapshots/finance/ft_gl_distribution/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- importable Domain XML: `domains/exports/manual_imports/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- Domain resource root: `FT_GL_DISTRIBUTION_RPT_CURR`
- refresh pattern: one-time baseline full rebuild, then rolling `12-month` `DELETE + INSERT + COMMIT`
- scheduler interval: every 6 hours at `03:00`, `09:00`, `15:00`, and `21:00 GMT`
- primary additive measures: `GL_AMOUNT`, `STATISTIC_AMOUNT`
- derived reporting measures stored in the snapshot: `DEBIT_AMT`, `CREDIT_AMT`
- batch provenance fields: `BATCH_CD` and `BATCH_NBR` from the latest `CI_FT_PROC` row per `FT_ID`; `IS_LATEST_BATCH_NBR` retained but not populated in the current release
- source population: all `CI_FT_GL` rows tied to non-redundant `CI_FT` rows where `CI_FT.REDUNDANT_SW = 'N'`
- final QA status: `Pass`
- ready for ad hoc use: `Yes`

## What This Snapshot Is
This snapshot is the governed finance detail layer for GL distribution reporting.

It answers questions like:
- how many GL lines exist by FT type, GL account, and distribution code
- what GL amount and statistic amount were posted
- which FT header each GL line belongs to
- which account, SA, and customer context the GL line is associated with
- which bill segment, adjustment, payment segment, and balance-control-group context is related to the FT

It is intentionally not an FT-header-only object.

It is not for:
- unduplicated FT header totals
- one-row-per-FT analysis
- finance summary questions where one FT should appear only once

Those belong in `FT_RPT_CURR`.

## Original Design Problem
The original FT / GL domain concept tried to answer both FT-header and GL-detail questions in one semantic shape.

What that original approach did well:
- started from the correct finance sources, `CI_FT` and `CI_FT_GL`
- carried useful finance, service, billing, adjustment, and payment context
- exposed enough detail to support GL reporting and reconciliation

What was wrong or insufficient about the original approach:
1. It did not establish one clear grain.
   The design mixed FT-level questions and GL-line questions in one reporting shape.
2. It allowed row-preservation risk.
   When FT detail and optional child tables are combined without a governed Oracle contract, users can misread repeated FT values as FT-level truth.
3. It was not operationally supportable.
   There was no single governed table plus procedure plus scheduler plus QA pack that DB or reporting support could inspect and rerun.
4. Some join behavior needed hardening.
   Optional child context had to be explicitly gated by FT family so that unrelated child tables did not accidentally populate across the wrong FT types.
5. Description handling was not governed enough.
   The final snapshot needed a repeatable Oracle-side contract for business-facing descriptions rather than leaving those expectations to report design or ad hoc interpretation.

## What Was Corrected In The Final Snapshot
The final governed FT GL snapshot fixes the original design issues in these specific ways.

### 1. The grain is explicit
The final governed object is one row per `CI_FT_GL` line.

That means:
- each row is identified by `FT_ID` + `GL_SEQ_NBR`
- FT header attributes are repeated on each GL line by design
- GL amounts remain fully additive at GL-line grain

Why this matters:
- users know exactly what one row means
- GL account and distribution-code reporting is stable
- finance detail totals reconcile cleanly back to `CI_FT_GL`

### 2. FT header and GL detail are separated correctly
The final design accepts that FT attributes may repeat across multiple GL lines, because this is a GL-line snapshot, not an FT-header snapshot.

Why this matters:
- one object can safely answer GL-line questions
- FT-header truth remains in a separate governed object
- analysts are less likely to aggregate repeated FT values incorrectly

### 3. Optional child context is gated by FT family
The final procedure only populates optional child overlays when the FT family supports them:
- `BS`, `BX` for bill segment context
- `AD`, `AX` for adjustment context
- `PS`, `PX` for payment segment context

Why this matters:
- unrelated child fields do not bleed across FT families
- source population is preserved
- context columns remain interpretable

### 4. The reporting logic now lives in Oracle
Instead of depending on a report/domain shape to represent the business logic, the final design uses:
- a physical snapshot table
- a stored refresh procedure
- a scheduler job
- repeatable validation and intensive QA SQL

Why this matters:
- support staff can inspect the real DB objects
- refresh behavior is controlled and repeatable
- QA can be rerun without reverse-engineering the design

### 5. Business context is persisted in the snapshot
The final snapshot carries business-readable descriptions for major user-facing dimensions, including:
- FT type
- GL distribution status
- distribution code
- GL division
- SA status
- SA type
- bill cycle
- customer class
- collection class
- account management group
- balancing status
- bill segment status and bill-cycle context
- bill segment cancel reason
- adjustment status, type, and cancel reason

Why this matters:
- ad hoc users can work from readable labels
- technical users still have raw codes for traceability
- report authors do not need to rebuild the same translations repeatedly

## Design Promise
The design promise is:

"For each non-redundant FT GL line, publish exactly one row with the GL-line measures intact and the most useful FT, account, service, balance-control, bill-segment, adjustment, and payment context flattened onto that line."

That means:
- the driver is `CI_FT_GL`
- only GL lines whose parent FT is non-redundant are included
- FT header values repeat by design across the FT's GL lines
- the object is meant for GL detail truth, not FT header truth

## Population Boundary
Current governed population:

```sql
FROM cisadm.ci_ft_gl ft_gl
INNER JOIN cisadm.ci_ft ft
    ON ft.ft_id = ft_gl.ft_id
   AND ft.redundant_sw = 'N'
```

Included FT families validated in QA:
- `AD`
- `AX`
- `BS`
- `BX`
- `PS`
- `PX`

Why this boundary was chosen:
- GL detail should include the full non-redundant finance population
- excluding FT families would turn the snapshot into a partial finance view instead of a governed GL-detail layer

## Grain And Join Safety Rules
The grain is one row per `FT_ID`, `GL_SEQ_NBR`.

This is protected by:
- driving from `CI_FT_GL`
- inner joining to `CI_FT` only to retain non-redundant parent FT rows
- using `LEFT JOIN`s for optional enrichment tables
- gating bill-segment, adjustment, and payment joins by FT family
- using a ranked customer subquery so one customer row is chosen per account instead of multiplying the GL line

This prevents:
- row multiplication from multiple account-person rows
- accidental loss of GL lines from inner joins to optional context
- ambiguous mixed-grain reporting

## Final Table Contract
The final table DDL is:

```sql
CREATE TABLE cisadm.ft_gl_distribution_rpt_curr (
    ft_id                              VARCHAR2(30)    NOT NULL,
    gl_seq_nbr                         NUMBER(18,0)    NOT NULL,
    gl_acct                            VARCHAR2(100),
    dst_id                             VARCHAR2(30),
    dst_desc                           VARCHAR2(254),
    gl_amount                          NUMBER(15,2),
    debit_amt                          NUMBER(15,2),
    credit_amt                         NUMBER(15,2),
    statistic_amount                   NUMBER,
    tot_amt_sw                         VARCHAR2(5),
    char_type_cd                       VARCHAR2(30),
    char_val                           VARCHAR2(254),
    batch_cd                           VARCHAR2(30),
    batch_nbr                          NUMBER(18,0),
    is_latest_batch_nbr                VARCHAR2(5),
    load_dttm                          TIMESTAMP DEFAULT SYSTIMESTAMP,
    ft_type_flg                        VARCHAR2(5),
    ft_type_flg_desc                   VARCHAR2(60),
    accounting_dt                      DATE,
    ars_dt                             DATE,
    ft_cre_dttm                        TIMESTAMP,
    freeze_sw                          VARCHAR2(5),
    freeze_dttm                        TIMESTAMP,
    freeze_user_id                     VARCHAR2(30),
    freeze_user_name                   VARCHAR2(200),
    cur_amt                            NUMBER(15,2),
    tot_amt                            NUMBER(15,2),
    currency_cd                        VARCHAR2(10),
    bill_id                            VARCHAR2(30),
    sa_id                              VARCHAR2(30),
    parent_id                          VARCHAR2(30),
    sibling_id                         VARCHAR2(30),
    gl_distrib_status                  VARCHAR2(5),
    gl_distrib_status_desc             VARCHAR2(60),
    gl_division                        VARCHAR2(30),
    gl_division_desc                   VARCHAR2(254),
    cis_division                       VARCHAR2(30),
    sched_distrib_dt                   DATE,
    xferred_out_sw                     VARCHAR2(5),
    xfer_to_gl_dt                      DATE,
    match_evt_id                       VARCHAR2(30),
    bal_ctl_grp_id                     NUMBER(18,0),
    correction_sw                      VARCHAR2(5),
    new_debit_sw                       VARCHAR2(5),
    show_on_bill_sw                    VARCHAR2(5),
    not_in_ars_sw                      VARCHAR2(5),
    acct_id                            VARCHAR2(30),
    per_id                             VARCHAR2(30),
    customer_name_upr                  VARCHAR2(200),
    sa_status_flg                      VARCHAR2(10),
    sa_status_desc                     VARCHAR2(100),
    sa_type_cd                         VARCHAR2(10),
    sa_type_desc                       VARCHAR2(100),
    char_prem_id                       VARCHAR2(30),
    bill_cyc_cd                        VARCHAR2(10),
    bill_cyc_desc                      VARCHAR2(100),
    cust_cl_cd                         VARCHAR2(10),
    cust_cl_desc                       VARCHAR2(100),
    coll_cl_cd                         VARCHAR2(10),
    coll_cl_desc                       VARCHAR2(100),
    acct_mgmt_grp_cd                   VARCHAR2(10),
    acct_mgmt_grp_desc                 VARCHAR2(100),
    balancing_stat_flg                 VARCHAR2(10),
    balancing_stat_desc                VARCHAR2(100),
    bcg_cur_amt                        NUMBER(15,2),
    bcg_tot_amt                        NUMBER(15,2),
    bcg_cur_bal                        NUMBER(15,2),
    bcg_tot_bal                        NUMBER(15,2),
    bcg_cre_dttm                       TIMESTAMP,
    bseg_id                            VARCHAR2(30),
    bseg_stat_flg                      VARCHAR2(10),
    bseg_stat_desc                     VARCHAR2(100),
    bseg_bill_cyc_cd                   VARCHAR2(10),
    bseg_bill_cyc_desc                 VARCHAR2(100),
    bseg_start_dt                      DATE,
    bseg_end_dt                        DATE,
    bseg_prem_id                       VARCHAR2(30),
    bseg_est_sw                        VARCHAR2(5),
    bseg_closing_sw                    VARCHAR2(5),
    bseg_can_rsn_cd                    VARCHAR2(10),
    bseg_can_rsn_desc                  VARCHAR2(100),
    adj_id                             VARCHAR2(30),
    adj_status_flg                     VARCHAR2(10),
    adj_status_desc                    VARCHAR2(100),
    adj_type_cd                        VARCHAR2(10),
    adj_type_desc                      VARCHAR2(100),
    adj_can_rsn_cd                     VARCHAR2(10),
    adj_can_rsn_desc                   VARCHAR2(100),
    adj_amt                            NUMBER(15,2),
    xfer_adj_id                        VARCHAR2(30),
    behalf_sa_id                       VARCHAR2(30),
    base_amt                           NUMBER(15,2),
    gen_ref_dt                         DATE,
    appr_req_id                        VARCHAR2(30),
    pay_seg_id                         VARCHAR2(30),
    pay_id                             VARCHAR2(30),
    pay_seg_amt                        NUMBER(15,2),
    pay_match_evt_id                   VARCHAR2(30)
);
```

## Field Inventory With Meaning
### GL line fields
- `FT_ID`: parent financial transaction ID
- `GL_SEQ_NBR`: GL-line sequence number inside the FT
- `GL_ACCT`: chart-of-accounts account
- `DST_ID`: distribution code ID
- `DST_DESC`: distribution code description
- `GL_AMOUNT`: GL-line amount
- `DEBIT_AMT`: derived debit amount from non-negative `GL_AMOUNT`
- `CREDIT_AMT`: derived credit amount from negative `GL_AMOUNT`
- `STATISTIC_AMOUNT`: statistic quantity or amount at GL-line grain
- `TOT_AMT_SW`: source total-amount switch
- `CHAR_TYPE_CD`: GL characteristic type code
- `CHAR_VAL`: GL characteristic value
- `BATCH_CD`: latest batch control code from `CI_FT_PROC` for the FT
- `BATCH_NBR`: latest batch number from `CI_FT_PROC` for the FT
- `IS_LATEST_BATCH_NBR`: reserved field; intentionally left null in the current release shape
- `LOAD_DTTM`: snapshot load timestamp

### FT header fields repeated on the GL line
- `FT_TYPE_FLG`, `FT_TYPE_FLG_DESC`
- `ACCOUNTING_DT`
- `ARS_DT`
- `FT_CRE_DTTM`
- `FREEZE_SW`
- `FREEZE_DTTM`
- `FREEZE_USER_ID`
- `FREEZE_USER_NAME`
- `CUR_AMT`
- `TOT_AMT`
- `CURRENCY_CD`
- `BILL_ID`
- `SA_ID`
- `PARENT_ID`
- `SIBLING_ID`
- `GL_DISTRIB_STATUS`, `GL_DISTRIB_STATUS_DESC`
- `GL_DIVISION`, `GL_DIVISION_DESC`
- `CIS_DIVISION`
- `SCHED_DISTRIB_DT`
- `XFERRED_OUT_SW`
- `XFER_TO_GL_DT`
- `MATCH_EVT_ID`
- `BAL_CTL_GRP_ID`
- `CORRECTION_SW`
- `NEW_DEBIT_SW`
- `SHOW_ON_BILL_SW`
- `NOT_IN_ARS_SW`

### Account and service fields
- `ACCT_ID`
- `PER_ID`
- `CUSTOMER_NAME_UPR`
- `SA_STATUS_FLG`, `SA_STATUS_DESC`
- `SA_TYPE_CD`, `SA_TYPE_DESC`
- `CHAR_PREM_ID`
- `BILL_CYC_CD`, `BILL_CYC_DESC`
- `CUST_CL_CD`, `CUST_CL_DESC`
- `COLL_CL_CD`, `COLL_CL_DESC`
- `ACCT_MGMT_GRP_CD`, `ACCT_MGMT_GRP_DESC`

### Balance control group fields
- `BALANCING_STAT_FLG`, `BALANCING_STAT_DESC`
- `BCG_CUR_AMT`
- `BCG_TOT_AMT`
- `BCG_CUR_BAL`
- `BCG_TOT_BAL`
- `BCG_CRE_DTTM`

### Bill segment fields
- `BSEG_ID`
- `BSEG_STAT_FLG`, `BSEG_STAT_DESC`
- `BSEG_BILL_CYC_CD`, `BSEG_BILL_CYC_DESC`
- `BSEG_START_DT`
- `BSEG_END_DT`
- `BSEG_PREM_ID`
- `BSEG_EST_SW`
- `BSEG_CLOSING_SW`
- `BSEG_CAN_RSN_CD`, `BSEG_CAN_RSN_DESC`

### Adjustment fields
- `ADJ_ID`
- `ADJ_STATUS_FLG`, `ADJ_STATUS_DESC`
- `ADJ_TYPE_CD`, `ADJ_TYPE_DESC`
- `ADJ_CAN_RSN_CD`, `ADJ_CAN_RSN_DESC`
- `ADJ_AMT`
- `XFER_ADJ_ID`
- `BEHALF_SA_ID`
- `BASE_AMT`
- `GEN_REF_DT`
- `APPR_REQ_ID`

### Payment fields
- `PAY_SEG_ID`
- `PAY_ID`
- `PAY_SEG_AMT`
- `PAY_MATCH_EVT_ID`

## Final Refresh Procedure
The final procedure logic is:

```sql
CREATE OR REPLACE PROCEDURE cisadm.refresh_ft_gl_distribution_rpt_curr AS
BEGIN
    EXECUTE IMMEDIATE 'TRUNCATE TABLE cisadm.ft_gl_distribution_rpt_curr';

    INSERT INTO cisadm.ft_gl_distribution_rpt_curr (...)
    SELECT
        ft.ft_id,
        ft_gl.gl_seq_nbr,
        ft_gl.gl_acct,
        ft_gl.dst_id,
        dst_l.descr,
        ft_gl.amount,
        ft_gl.statistic_amount,
        ft_gl.tot_amt_sw,
        ft_gl.char_type_cd,
        ft_gl.char_val,
        SYSTIMESTAMP,
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
        ft.ars_dt,
        ft.cre_dttm,
        ft.freeze_sw,
        ft.freeze_dttm,
        ft.freeze_user_id,
        TRIM(sc_user.first_name || ' ' || sc_user.last_name),
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
        ft.gl_division,
        gl_div_l.descr,
        ft.cis_division,
        ft.sched_distrib_dt,
        ft.xferred_out_sw,
        ft.xfer_to_gl_dt,
        ft.match_evt_id,
        ft.bal_ctl_grp_id,
        ft.correction_sw,
        ft.new_debit_sw,
        ft.show_on_bill_sw,
        ft.not_in_ars_sw,
        sa.acct_id,
        cust.per_id,
        cust.entity_name_upr,
        sa.sa_status_flg,
        sa_status_l.descr,
        sa.sa_type_cd,
        sa_type_l.descr,
        sa.char_prem_id,
        acct.bill_cyc_cd,
        acct_bill_cyc_l.descr,
        acct.cust_cl_cd,
        cust_cl_l.descr,
        acct.coll_cl_cd,
        coll_cl_l.descr,
        acct.acct_mgmt_grp_cd,
        acct_mgmt_l.descr,
        bcg.balancing_stat_flg,
        bcg_status_l.descr,
        bcg.cur_amt,
        bcg.tot_amt,
        bcg.cur_bal,
        bcg.tot_bal,
        bcg.cre_dttm,
        bseg.bseg_id,
        bseg.bseg_stat_flg,
        bseg_status_l.descr,
        bseg.bill_cyc_cd,
        bseg_bill_cyc_l.descr,
        bseg.start_dt,
        bseg.end_dt,
        bseg.prem_id,
        bseg.est_sw,
        bseg.closing_bseg_sw,
        bseg.can_rsn_cd,
        bseg_can_rsn_l.descr,
        adj.adj_id,
        adj.adj_status_flg,
        adj_status_l.descr,
        adj.adj_type_cd,
        adj_type_l.descr,
        adj.can_rsn_cd,
        adj_can_rsn_l.descr,
        adj.adj_amt,
        adj.xfer_adj_id,
        adj.behalf_sa_id,
        adj.base_amt,
        adj.gen_ref_dt,
        adj.appr_req_id,
        pay_seg.pay_seg_id,
        pay_seg.pay_id,
        pay_seg.pay_seg_amt,
        pay_seg.match_evt_id
    FROM cisadm.ci_ft_gl ft_gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = ft_gl.ft_id
       AND ft.redundant_sw = 'N'
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ft.sibling_id
       AND bseg.bill_id = ft.bill_id
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_adj adj
        ON adj.adj_id = ft.sibling_id
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_pay_seg pay_seg
        ON pay_seg.pay_seg_id = ft.sibling_id
       AND pay_seg.pay_id = ft.parent_id
       AND ft.ft_type_flg IN ('PS', 'PX')
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = ft.sa_id
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    LEFT JOIN (
        SELECT
            ap.acct_id,
            ap.per_id,
            pn.entity_name_upr,
            ROW_NUMBER() OVER (
                PARTITION BY ap.acct_id
                ORDER BY
                    CASE WHEN ap.fin_resp_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN ap.main_cust_sw = 'Y' THEN 0 ELSE 1 END,
                    CASE WHEN pn.prim_name_sw = 'Y' THEN 0 ELSE 1 END,
                    pn.seq_num,
                    ap.per_id
            ) AS rn
        FROM cisadm.ci_acct_per ap
        INNER JOIN cisadm.ci_per_name pn
            ON pn.per_id = ap.per_id
        WHERE ap.main_cust_sw = 'Y'
           OR ap.fin_resp_sw = 'Y'
    ) cust
        ON cust.acct_id = sa.acct_id
       AND cust.rn = 1
    LEFT JOIN cisadm.ci_gl_division_l gl_div_l
        ON gl_div_l.gl_division = ft.gl_division
       AND gl_div_l.language_cd = 'ENG'
    LEFT JOIN cisadm.sc_user sc_user
        ON sc_user.user_id = ft.freeze_user_id
    LEFT JOIN cisadm.ci_lookup_val_l sa_status_l
        ON sa_status_l.field_name = 'SA_STATUS_FLG'
       AND sa_status_l.field_value = sa.sa_status_flg
       AND sa_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.cis_division = sa.cis_division
       AND sa_type_l.sa_type_cd = sa.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bill_cyc_l acct_bill_cyc_l
        ON acct_bill_cyc_l.bill_cyc_cd = acct.bill_cyc_cd
       AND acct_bill_cyc_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_cust_cl_l cust_cl_l
        ON cust_cl_l.cust_cl_cd = acct.cust_cl_cd
       AND cust_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_coll_cl_l coll_cl_l
        ON coll_cl_l.coll_cl_cd = acct.coll_cl_cd
       AND coll_cl_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_acct_mgmt_gr_l acct_mgmt_l
        ON acct_mgmt_l.acct_mgmt_grp_cd = acct.acct_mgmt_grp_cd
       AND acct_mgmt_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_bal_ctl_grp bcg
        ON bcg.bal_ctl_grp_id = ft.bal_ctl_grp_id
    LEFT JOIN cisadm.ci_lookup_val_l bcg_status_l
        ON bcg_status_l.field_name = 'BALANCING_STAT_FLG'
       AND bcg_status_l.field_value = bcg.balancing_stat_flg
       AND bcg_status_l.language_cd = 'ENG'
    LEFT JOIN cisadm.ci_lookup_val_l bseg_status_l
        ON bseg_status_l.field_name = 'BSEG_STAT_FLG'
       AND bseg_status_l.field_value = bseg.bseg_stat_flg
       AND bseg_status_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_bill_cyc_l bseg_bill_cyc_l
        ON bseg_bill_cyc_l.bill_cyc_cd = bseg.bill_cyc_cd
       AND bseg_bill_cyc_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_bill_can_rsn_l bseg_can_rsn_l
        ON bseg_can_rsn_l.can_rsn_cd = bseg.can_rsn_cd
       AND bseg_can_rsn_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('BS', 'BX')
    LEFT JOIN cisadm.ci_lookup_val_l adj_status_l
        ON adj_status_l.field_name = 'ADJ_STATUS_FLG'
       AND adj_status_l.field_value = adj.adj_status_flg
       AND adj_status_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_adj_type_l adj_type_l
        ON adj_type_l.adj_type_cd = adj.adj_type_cd
       AND adj_type_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_adj_can_rsn_l adj_can_rsn_l
        ON adj_can_rsn_l.can_rsn_cd = adj.can_rsn_cd
       AND adj_can_rsn_l.language_cd = 'ENG'
       AND ft.ft_type_flg IN ('AD', 'AX')
    LEFT JOIN cisadm.ci_dst_code_l dst_l
        ON dst_l.dst_id = ft_gl.dst_id
       AND dst_l.language_cd = 'ENG';

    COMMIT;
END;
/
```

## Why The Final Procedure Looks This Way
Specific final design decisions:
- the active procedure now refreshes only the last `12` accounting months because diagnostics showed no recent back-posting into periods older than `12` months
- the full-history `TRUNCATE + INSERT + COMMIT` version is still preserved separately for one-time baseline loads
- `STATISTIC_AMOUNT` is stored without forced two-decimal scale so the source precision is not lost
- the parent FT filter is applied in the `INNER JOIN` to `CI_FT` so only non-redundant FT populations survive
- batch metadata is sourced from the latest ranked `CI_FT_PROC` row per `FT_ID`
- bill segment, adjustment, and payment joins are explicitly gated by FT type
- one customer row per account is selected with `ROW_NUMBER()` to avoid row multiplication
- descriptions are resolved during refresh so Jasper does not need to recreate translation logic

## Scheduler Definition
The final scheduler SQL is:

```sql
BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=3,9,15,21;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh FT GL distribution snapshot every 6 hours at 03:00, 09:00, 15:00, and 21:00 GMT'
    );
END;
/
```

Operational meaning:
- first eligible run is the next `03:00`, `09:00`, `15:00`, or `21:00 GMT` scheduler slot after creation
- then runs every 6 hours at `03:00`, `09:00`, `15:00`, and `21:00 GMT`
- because the active pattern is rolling-window maintenance, the empty-table exposure risk is reduced compared with the original full rebuild

## Domain Contract
The final Domain is a single-table JDBC Domain on `FT_GL_DISTRIBUTION_RPT_CURR` using datasource alias `Origin_DEV_DS` and schema alias `CISADM`.

Exact final XML implementation facts:
- file name: `FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- top item group id: `FT_GL_DISTRIBUTION_RPT_CURR`
- top label: `Financial Transaction GL Distribution`
- physical source block: `<jdbcTable id="FT_GL_DISTRIBUTION_RPT_CURR" datasourceId="Origin_DEV_DS" datasourceTableName="FT_GL_DISTRIBUTION_RPT_CURR" schemaAlias="CISADM">`
- design approach: single physical table, no Domain-side join tree

Final item groups exposed:
- `GL_LINE`
- `FT_CORE`
- `ACCT_SERVICE`
- `BALANCE_CONTROL`
- `BILL_SEGMENT`
- `ADJUSTMENT_TRACE`
- `PAYMENT_SEGMENT`
- `SNAPSHOT_AUDIT`

Final user-facing field list by group:

`GL_LINE`
- `FT_ID`
- `GL_SEQ_NBR`
- `GL_ACCT`
- `DST_DESC`
- `DST_ID`
- `GL_AMOUNT`
- `STATISTIC_AMOUNT`
- `TOT_AMT_SW`
- `CHAR_TYPE_CD`
- `CHAR_VAL`
- `BATCH_CD`
- `BATCH_NBR`
- `IS_LATEST_BATCH_NBR`

`FT_CORE`
- `FT_TYPE_FLG_DESC`
- `FT_TYPE_FLG`
- `ACCOUNTING_DT`
- `ARS_DT`
- `FT_CRE_DTTM`
- `CUR_AMT`
- `TOT_AMT`
- `CURRENCY_CD`
- `BILL_ID`
- `PARENT_ID`
- `SIBLING_ID`
- `GL_DISTRIB_STATUS_DESC`
- `GL_DISTRIB_STATUS`
- `GL_DIVISION_DESC`
- `GL_DIVISION`
- `CIS_DIVISION`
- `SCHED_DISTRIB_DT`
- `XFERRED_OUT_SW`
- `XFER_TO_GL_DT`
- `MATCH_EVT_ID`
- `CORRECTION_SW`
- `NEW_DEBIT_SW`
- `SHOW_ON_BILL_SW`
- `NOT_IN_ARS_SW`

`ACCT_SERVICE`
- `CUSTOMER_NAME_UPR`
- `PER_ID`
- `ACCT_ID`
- `SA_ID`
- `SA_STATUS_DESC`
- `SA_STATUS_FLG`
- `SA_TYPE_DESC`
- `SA_TYPE_CD`
- `CHAR_PREM_ID`
- `BILL_CYC_DESC`
- `BILL_CYC_CD`
- `CUST_CL_DESC`
- `CUST_CL_CD`
- `COLL_CL_DESC`
- `COLL_CL_CD`
- `ACCT_MGMT_GRP_DESC`
- `ACCT_MGMT_GRP_CD`

`BALANCE_CONTROL`
- `BAL_CTL_GRP_ID`
- `BALANCING_STAT_DESC`
- `BALANCING_STAT_FLG`
- `BCG_CUR_AMT`
- `BCG_TOT_AMT`
- `BCG_CUR_BAL`
- `BCG_TOT_BAL`
- `BCG_CRE_DTTM`

`BILL_SEGMENT`
- `BSEG_ID`
- `BSEG_STAT_DESC`
- `BSEG_STAT_FLG`
- `BSEG_BILL_CYC_DESC`
- `BSEG_BILL_CYC_CD`
- `BSEG_START_DT`
- `BSEG_END_DT`
- `BSEG_PREM_ID`
- `BSEG_EST_SW`
- `BSEG_CLOSING_SW`
- `BSEG_CAN_RSN_DESC`
- `BSEG_CAN_RSN_CD`

`ADJUSTMENT_TRACE`
- `ADJ_ID`
- `ADJ_STATUS_DESC`
- `ADJ_STATUS_FLG`
- `ADJ_TYPE_DESC`
- `ADJ_TYPE_CD`
- `ADJ_CAN_RSN_DESC`
- `ADJ_CAN_RSN_CD`
- `ADJ_AMT`
- `XFER_ADJ_ID`
- `BEHALF_SA_ID`
- `BASE_AMT`
- `GEN_REF_DT`
- `APPR_REQ_ID`

`PAYMENT_SEGMENT`
- `PAY_SEG_ID`
- `PAY_ID`
- `PAY_SEG_AMT`
- `PAY_MATCH_EVT_ID`

`SNAPSHOT_AUDIT`
- `FREEZE_SW`
- `FREEZE_DTTM`
- `FREEZE_USER_NAME`
- `FREEZE_USER_ID`
- `LOAD_DTTM`

## Why These Domain Fields Were Exposed
Final exposure logic:
- all GL-line truth fields are exposed because this object exists to answer GL-detail questions
- major business dimensions keep both code and description
- technical switch and trace fields remain in the Domain because the business chose to keep them available for audit and debug use
- FT header context is included because users often need FT type, status, and bill or service context while analyzing GL distribution lines

## Step-By-Step Replication
### Build from scratch
1. Create the table using the full DDL shown above.
2. Create the procedure using the full procedure logic shown above.
3. Run the manual refresh:

```sql
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
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
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/
```

### Snapshot row count
```sql
SELECT COUNT(*) AS snapshot_count
FROM cisadm.ft_gl_distribution_rpt_curr;
```

### Source row count
```sql
SELECT COUNT(*) AS source_count
FROM cisadm.ci_ft_gl gl
INNER JOIN cisadm.ci_ft ft
    ON ft.ft_id = gl.ft_id
WHERE ft.redundant_sw = 'N';
```

### Duplicate natural-key check
```sql
SELECT
    ft_id,
    gl_seq_nbr,
    COUNT(*) AS row_count
FROM cisadm.ft_gl_distribution_rpt_curr
GROUP BY
    ft_id,
    gl_seq_nbr
HAVING COUNT(*) > 1;
```

### Description coverage check
```sql
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_type_flg_desc IS NULL THEN 1 ELSE 0 END) AS missing_ft_type_desc,
    SUM(CASE WHEN gl_distrib_status_desc IS NULL AND gl_distrib_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_gl_status_desc,
    SUM(CASE WHEN dst_desc IS NULL AND dst_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_dst_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN customer_name_upr IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN balancing_stat_desc IS NULL AND balancing_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_balancing_status_desc,
    SUM(CASE WHEN freeze_user_name IS NULL AND freeze_user_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_freeze_user_name
FROM cisadm.ft_gl_distribution_rpt_curr;
```

### Amount reconciliation
```sql
SELECT
    SUM(gl_amount) AS snap_gl_amount,
    SUM(statistic_amount) AS snap_statistic_amount
FROM cisadm.ft_gl_distribution_rpt_curr;

SELECT
    SUM(gl.amount) AS src_gl_amount,
    SUM(gl.statistic_amount) AS src_statistic_amount
FROM cisadm.ci_ft_gl gl
INNER JOIN cisadm.ci_ft ft
    ON ft.ft_id = gl.ft_id
WHERE ft.redundant_sw = 'N';
```

### FT type profile inside GL lines
```sql
SELECT
    gl_acct,
    dst_id,
    ft_type_flg,
    ft_type_flg_desc,
    COUNT(*) AS gl_line_count,
    COUNT(DISTINCT ft_id) AS ft_count,
    SUM(gl_amount) AS gl_amount
FROM cisadm.ft_gl_distribution_rpt_curr
GROUP BY
    gl_acct,
    dst_id,
    ft_type_flg,
    ft_type_flg_desc
ORDER BY
    gl_acct,
    dst_id,
    ft_type_flg;
```

## Intensive QA SQL To Run
Run these after the validation layer.

Key sections in the QA pack:
- source vs snapshot GL-line baseline
- anti-join counts
- overall row and amount parity
- FT-type-level parity
- GL-account and distribution-code parity
- GL-line count parity by FT
- child-overlay and context-coverage parity
- description and lookup parity
- raw-code-only field audit

## Actual QA Results
Final recorded QA result:
- pass/fail: `Pass`
- ready for ad hoc use: `Yes`

### Source parity
- source GL line count: `4,954,576`
- snapshot GL line count: `4,954,576`
- count difference: `0`
- source distinct `FT_ID` count: `2,322,703`
- snapshot distinct `FT_ID` count: `2,322,703`
- distinct FT difference: `0`
- source `GL_AMOUNT`: `0`
- snapshot `GL_AMOUNT`: `0`
- `GL_AMOUNT` difference: `0`
- source `STATISTIC_AMOUNT`: `475,046,395`
- snapshot `STATISTIC_AMOUNT`: `475,046,395`
- `STATISTIC_AMOUNT` difference: `0`

### Anti-joins and key safety
- source GL lines missing in snapshot: `0`
- snapshot GL lines not in source: `0`
- duplicate `FT_ID`, `GL_SEQ_NBR` rows: `0`
- GL-account and distribution-code parity differences: `0 rows returned`
- FT-family-level parity: exact across all six validated FT families

### Context and overlay parity
- account context parity: `Pass`
- person trace parity: `Pass`
- bill segment overlay parity: `Pass`
- adjustment overlay parity: `Pass`
- payment segment overlay parity: `Pass`
- balance-control-group ID parity: `Pass`
- balance-control-group status and description parity: `Pass`

### Batch provenance parity
- `BATCH_CD` mismatched rows: `0`
- `BATCH_NBR` mismatched rows: `0`
- `IS_LATEST_BATCH_NBR` mismatched rows: `4,184`

Interpretation:
- batch code and batch number provenance matched exactly against the source latest `CI_FT_PROC` row per `FT_ID`
- the latest-batch flag mismatches are expected because the current procedure intentionally leaves `IS_LATEST_BATCH_NBR` null
- latest-batch filtering, if needed, is a manual or report-side decision in the accepted release shape

### Description parity
Mismatch counts were `0` for:
- FT type description
- GL distribution status description
- distribution-code description
- GL division description
- SA status description
- SA type description
- bill cycle description
- customer class description
- collection class description
- account management group description
- balancing status description
- bill segment description
- adjustment description
- freeze user name

### Remaining source lookup gaps
These are source-data coverage gaps, not snapshot logic defects:
- `DST_ID`: `77`
- `SA_TYPE_CD`: `52`
- `BILL_CYC_CD`: `1,353`
- `ACCT_MGMT_GRP_CD`: `4,954,576` rows; populated code exists but maintained lookup translation is absent
- `BSEG_BILL_CYC_CD`: `42,768`
- `BSEG_CAN_RSN_CD`: `2,161,849`
- `ADJ_TYPE_CD`: `70`
- `ADJ_CAN_RSN_CD`: `544,862`

Interpretation:
- where a source lookup exists, the snapshot matches it
- remaining issues are tenant lookup maintenance issues, not reasons to reject the snapshot

## Final Decisions On Business Context
### Kept in the snapshot
- all GL-line truth fields
- FT header context repeated on each GL line
- account, service, customer, balance-control, bill-segment, adjustment, and payment overlays
- technical switch and trace fields such as `TOT_AMT_SW`, `FREEZE_SW`, `XFERRED_OUT_SW`, `CORRECTION_SW`, `NEW_DEBIT_SW`, `SHOW_ON_BILL_SW`, `NOT_IN_ARS_SW`, `CHAR_TYPE_CD`, and `CURRENCY_CD`

### Why kept
- finance support needs traceability at GL-line grain
- ad hoc users may need to debug unusual postings without asking for a new extract
- the business explicitly accepted keeping these fields available rather than stripping them out

### What not to do with this snapshot
- do not use it for unduplicated FT totals
- do not sum `CUR_AMT` or `TOT_AMT` as if one row equals one FT
- do not treat repeated FT fields as FT-header grain measures

## SQL Developer Debugging Steps
### Check the table
```sql
SELECT COUNT(*) AS row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.ft_gl_distribution_rpt_curr;
```

### Inspect sample rows
```sql
SELECT *
FROM cisadm.ft_gl_distribution_rpt_curr
FETCH FIRST 25 ROWS ONLY;
```

### View the procedure text
```sql
SELECT line, text
FROM all_source
WHERE owner = 'CISADM'
  AND name = 'REFRESH_FT_GL_DISTRIBUTION_RPT_CURR'
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
  AND job_name = 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR';
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
  AND job_name = 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR'
ORDER BY log_id DESC
FETCH FIRST 20 ROWS ONLY;
```

### Disable the job
```sql
BEGIN
    DBMS_SCHEDULER.DISABLE('CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR');
END;
/
```

### Re-enable the job
```sql
BEGIN
    DBMS_SCHEDULER.ENABLE('CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR');
END;
/
```

### Manual refresh
```sql
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/
```

## How To Debug Common Problems
### If row counts do not match source
Check:
1. whether the join to `CI_FT` still enforces `REDUNDANT_SW = 'N'`
2. whether the natural key `FT_ID`, `GL_SEQ_NBR` has duplicates
3. whether any optional join was turned into an inner join
4. whether anti-join results show missing or extra rows

### If GL amounts or statistic amounts do not match
Check:
1. whether `STATISTIC_AMOUNT` has been rescaled or rounded
2. whether any row-multiplying join was introduced
3. whether a filter was added to the source population
4. whether the wrong numeric field is being aggregated

### If customer or person context looks duplicated or inconsistent
Check:
1. whether the ranked customer subquery still uses `ROW_NUMBER()`
2. whether `cust.rn = 1` is still enforced
3. whether anyone changed the account-person ranking logic

### If bill segment, adjustment, or payment fields look wrong
Check:
1. the FT family of the row
2. whether the child join still includes the FT-family gate
3. whether `BILL_ID`, `PARENT_ID`, and `SIBLING_ID` are still mapped the same way

### If descriptions are missing
Check:
1. whether the description column exists in the table
2. whether the procedure still selects it
3. whether the lookup exists in the tenant source table
4. whether the issue is a source lookup gap rather than a snapshot defect

### If the Domain is missing fields
Check:
1. whether the column exists in Oracle
2. whether the field exists in the Domain XML
3. whether the Jaspersoft Domain was reimported after the change

## Final Status
`FT_GL_DISTRIBUTION_RPT_CURR` is approved as the governed FT GL distribution snapshot.

It is:
- row-safe at GL-line grain
- numerically reconciled to source
- operationally refreshable
- documented for replication and debugging
- acceptable for ad hoc and reporting use

The remaining open issues are tenant lookup-maintenance gaps, not blockers to using the snapshot.
