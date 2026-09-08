-- Deep QA: source population vs snapshot, inner-join drop analysis, lookup coverage
-- Run: python3 scripts/local/run_client_oracle_sql.py --client demo --file sql/performance/snapshots/docs/consolidation_demo_deep_qa.sql

-- 1) ACCT_CUSTOMER: full account population
SELECT 'acct_customer' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_acct) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.acct_customer_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_acct a
     LEFT JOIN cisadm.acct_customer_rpt_curr s ON s.acct_id = a.acct_id
     WHERE s.acct_id IS NULL) AS missing_from_snap
FROM dual;

-- 2) CASE_PREM_CONTACT: CI_CASE vs CMS view vs snapshot
SELECT 'case_prem_contact' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_case) AS ci_case_cnt,
    (SELECT COUNT(*) FROM cisadm.cms_ci_case_vw) AS cms_vw_cnt,
    (SELECT COUNT(*) FROM cisadm.case_prem_contact_rpt_curr) AS snap_cnt
FROM dual;

-- 3) NEW_SERVICE_PIPELINE: scoped vs all SA
SELECT 'new_service_pipeline' AS snap, 'scope' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_sa) AS all_sa,
    (SELECT COUNT(*) FROM cisadm.ci_sa WHERE NULLIF(TRIM(sa_status_flg),'') IN ('10','20')) AS status_10_20,
    (SELECT COUNT(*) FROM cisadm.new_service_pipeline_rpt_curr) AS snap_cnt
FROM dual;

-- 4) FIELD_ACTIVITY: D1FA activities with/without BODA
SELECT 'field_activity' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.d1_activity act
     JOIN cisadm.d1_activity_type t ON t.activity_type_cd = act.activity_type_cd AND t.activity_type_cat_flg = 'D1FA') AS d1fa_cnt,
    (SELECT COUNT(*) FROM cisadm.d1_activity act
     JOIN cisadm.d1_activity_type t ON t.activity_type_cd = act.activity_type_cd AND t.activity_type_cat_flg = 'D1FA'
     JOIN cisadm.cms_d1_activity_d1fa_boda_vw b ON b.d1_activity_id = act.d1_activity_id) AS d1fa_with_boda,
    (SELECT COUNT(*) FROM cisadm.field_activity_rpt_curr) AS snap_cnt
FROM dual;

-- 5) CREW_OPS: one row per representative (BODA view can fan out)
SELECT 'crew_ops' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.c1_representative) AS all_crew,
    (SELECT COUNT(*) FROM cisadm.crew_ops_rpt_curr) AS snap_cnt,
    (SELECT COUNT(DISTINCT crew_id) FROM cisadm.crew_ops_rpt_curr) AS distinct_crew_in_snap
FROM dual;

-- 6) DEVICE_SP: all devices
SELECT 'device_sp' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.d1_dvc) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.device_sp_rpt_curr) AS snap_cnt
FROM dual;

-- 7) PAY_EVENT: all payments
SELECT 'pay_event' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_pay) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.pay_event_rpt_curr) AS snap_cnt
FROM dual;

-- 8) BILLABLE_CHARGE: charge lines vs snapshot (inner join drop test)
SELECT 'billable_charge' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_b_chg_line) AS all_lines,
    (SELECT COUNT(*) FROM cisadm.ci_b_chg_line bcl
     JOIN cisadm.ci_bill_chg bc ON bc.billable_chg_id = bcl.billable_chg_id
     JOIN cisadm.ci_sa sa ON sa.sa_id = bc.sa_id) AS lines_with_sa,
    (SELECT COUNT(*) FROM cisadm.ci_b_chg_line bcl
     JOIN cisadm.ci_bill_chg bc ON bc.billable_chg_id = bcl.billable_chg_id
     JOIN cisadm.ci_sa sa ON sa.sa_id = bc.sa_id
     JOIN cisadm.ci_sa_type st ON st.cis_division = sa.cis_division AND st.sa_type_cd = sa.sa_type_cd) AS lines_with_sa_type,
    (SELECT COUNT(*) FROM cisadm.billable_charge_rpt_curr) AS snap_cnt
FROM dual;

-- 9) SA_AGED_BAL: governed arrears population (matches refresh procedure logic)
SELECT 'sa_aged_bal' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM (
        SELECT ft.sa_id
        FROM cisadm.ci_ft ft
        WHERE ft.freeze_sw = 'Y'
          AND ft.not_in_ars_sw = 'N'
          AND ft.ft_type_flg NOT IN ('PS', 'PX')
          AND ft.ars_dt IS NOT NULL
        GROUP BY ft.sa_id
        HAVING SUM(ft.cur_amt) > 0
    )) AS sa_with_debt,
    (SELECT COUNT(*) FROM cisadm.sa_aged_bal_rpt_curr) AS snap_cnt
FROM dual;

-- 10) WO_PROC
SELECT 'wo_proc' AS snap, 'population' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_wo_proc) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.wo_proc_rpt_curr) AS snap_cnt
FROM dual;

-- 11) WORKFLOW_QUEUE todo parity
SELECT 'workflow_queue' AS snap, 'todo_parity' AS check_type,
    (SELECT COUNT(*) FROM cisadm.ci_td_entry) AS source_todo,
    (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr WHERE queue_source = 'TODO') AS snap_todo,
    (SELECT COUNT(*) FROM cisadm.ci_batch_inst) AS source_batch,
    (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr WHERE queue_source = 'BATCH') AS snap_batch
FROM dual;

-- Lookup coverage rollup (code populated, desc missing)
SELECT 'acct_customer' AS snap, COUNT(*) AS rows_with_missing_lookup_desc
FROM cisadm.acct_customer_rpt_curr
WHERE (bill_cyc_desc IS NULL AND NULLIF(TRIM(bill_cyc_cd),'') IS NOT NULL)
   OR (cust_cl_desc IS NULL AND NULLIF(TRIM(cust_cl_cd),'') IS NOT NULL)
   OR (coll_cl_desc IS NULL AND NULLIF(TRIM(coll_cl_cd),'') IS NOT NULL);

SELECT 'field_activity' AS snap, COUNT(*) AS missing_bo_status_desc
FROM cisadm.field_activity_rpt_curr
WHERE bo_status_desc IS NULL AND NULLIF(TRIM(bo_status_cd),'') IS NOT NULL;

SELECT 'crew_ops' AS snap, COUNT(*) AS missing_bo_status_desc
FROM cisadm.crew_ops_rpt_curr
WHERE bo_status_desc IS NULL AND NULLIF(TRIM(bo_status_cd),'') IS NOT NULL;

SELECT 'billable_charge' AS snap, COUNT(*) AS missing_stat_desc
FROM cisadm.billable_charge_rpt_curr
WHERE billable_chg_stat_desc IS NULL AND NULLIF(TRIM(billable_chg_stat),'') IS NOT NULL;
