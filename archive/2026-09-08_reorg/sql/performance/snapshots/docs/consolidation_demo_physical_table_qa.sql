-- Physical-table consolidation QA (demo)
-- Validates driving physical population vs snapshot; documents view-independent parity.
-- Run: python3 scripts/local/run_client_oracle_sql.py --client demo --file sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql

-- Snapshot | physical driver | expected parity
SELECT 'acct_customer' AS snap, 'CI_ACCT' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_acct) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.acct_customer_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_acct a
     LEFT JOIN cisadm.acct_customer_rpt_curr s ON s.acct_id = a.acct_id WHERE s.acct_id IS NULL) AS missing
FROM dual;

SELECT 'case_prem_contact' AS snap, 'CI_CASE' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_case) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.case_prem_contact_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_case cs
     LEFT JOIN cisadm.case_prem_contact_rpt_curr s ON s.case_id = cs.case_id WHERE s.case_id IS NULL) AS missing
FROM dual;

SELECT 'new_service_pipeline' AS snap, 'CI_SA' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_sa) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.new_service_pipeline_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_sa sa
     LEFT JOIN cisadm.new_service_pipeline_rpt_curr s ON s.sa_id = sa.sa_id WHERE s.sa_id IS NULL) AS missing
FROM dual;

SELECT 'field_activity' AS snap, 'D1_ACTIVITY (D1FA)' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.d1_activity act
     JOIN cisadm.d1_activity_type t ON t.activity_type_cd = act.activity_type_cd AND t.activity_type_cat_flg = 'D1FA') AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.field_activity_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.d1_activity act
     JOIN cisadm.d1_activity_type t ON t.activity_type_cd = act.activity_type_cd AND t.activity_type_cat_flg = 'D1FA'
     LEFT JOIN cisadm.field_activity_rpt_curr s ON s.d1_activity_id = act.d1_activity_id WHERE s.d1_activity_id IS NULL) AS missing
FROM dual;

SELECT 'crew_ops' AS snap, 'C1_REPRESENTATIVE' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.c1_representative) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.crew_ops_rpt_curr) AS snap_cnt,
    (SELECT COUNT(DISTINCT crew_id) FROM cisadm.crew_ops_rpt_curr) AS distinct_crew,
    (SELECT COUNT(*) FROM cisadm.c1_representative r
     LEFT JOIN cisadm.crew_ops_rpt_curr s ON s.crew_id = r.c1_representative_cd WHERE s.crew_id IS NULL) AS missing
FROM dual;

SELECT 'device_sp' AS snap, 'D1_DVC' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.d1_dvc) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.device_sp_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.d1_dvc d
     LEFT JOIN cisadm.device_sp_rpt_curr s ON s.d1_dvc_id = d.d1_device_id WHERE s.d1_dvc_id IS NULL) AS missing
FROM dual;

SELECT 'pay_event' AS snap, 'CI_PAY' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_pay) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.pay_event_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_pay p
     LEFT JOIN cisadm.pay_event_rpt_curr s ON s.pay_id = p.pay_id WHERE s.pay_id IS NULL) AS missing
FROM dual;

SELECT 'billable_charge' AS snap, 'CI_B_CHG_LINE+CI_BILL_CHG' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_b_chg_line bcl
     INNER JOIN cisadm.ci_bill_chg bc ON bc.billable_chg_id = bcl.billable_chg_id) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.billable_charge_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_b_chg_line bcl
     INNER JOIN cisadm.ci_bill_chg bc ON bc.billable_chg_id = bcl.billable_chg_id
     LEFT JOIN cisadm.billable_charge_rpt_curr s
       ON s.billable_chg_id = bcl.billable_chg_id AND s.line_seq = bcl.line_seq
     WHERE s.billable_chg_id IS NULL) AS missing
FROM dual;

SELECT 'sa_aged_bal' AS snap, 'CI_FT (governed debt)' AS physical_driver,
    (SELECT COUNT(*) FROM (
        SELECT ft.sa_id FROM cisadm.ci_ft ft
        WHERE ft.freeze_sw = 'Y' AND ft.not_in_ars_sw = 'N'
          AND ft.ft_type_flg NOT IN ('PS','PX') AND ft.ars_dt IS NOT NULL
        GROUP BY ft.sa_id HAVING SUM(ft.cur_amt) > 0)) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.sa_aged_bal_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM (
        SELECT ft.sa_id FROM cisadm.ci_ft ft
        WHERE ft.freeze_sw = 'Y' AND ft.not_in_ars_sw = 'N'
          AND ft.ft_type_flg NOT IN ('PS','PX') AND ft.ars_dt IS NOT NULL
        GROUP BY ft.sa_id HAVING SUM(ft.cur_amt) > 0) d
     LEFT JOIN cisadm.sa_aged_bal_rpt_curr s ON s.sa_id = d.sa_id WHERE s.sa_id IS NULL) AS missing
FROM dual;

SELECT 'wo_proc' AS snap, 'CI_WO_PROC' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_wo_proc) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.wo_proc_rpt_curr) AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_wo_proc wp
     LEFT JOIN cisadm.wo_proc_rpt_curr s ON s.wo_proc_id = wp.wo_proc_id WHERE s.wo_proc_id IS NULL) AS missing
FROM dual;

SELECT 'ops_exception' AS snap, 'multi-source union' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ops_exception_rpt_curr) AS snap_cnt,
    (SELECT COUNT(DISTINCT excp_source) FROM cisadm.ops_exception_rpt_curr) AS source_types
FROM dual;

SELECT 'ops_exception' AS snap, 'BSEG' AS excp_source,
    (SELECT COUNT(*) FROM cisadm.ci_bseg_excp) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.ops_exception_rpt_curr WHERE excp_source = 'BSEG') AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.ci_bseg_excp s
     LEFT JOIN cisadm.ops_exception_rpt_curr o
       ON o.excp_source = 'BSEG' AND o.excp_natural_key = s.bseg_id || '~' || s.bseg_excp_flg
     WHERE o.excp_natural_key IS NULL) AS missing
FROM dual;

SELECT 'ops_exception' AS snap, 'USAGE' AS excp_source,
    (SELECT COUNT(*) FROM cisadm.d1_usage_excp) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.ops_exception_rpt_curr WHERE excp_source = 'USAGE') AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.d1_usage_excp s
     LEFT JOIN cisadm.ops_exception_rpt_curr o ON o.excp_source = 'USAGE' AND o.excp_natural_key = s.usage_excp_id
     WHERE o.excp_natural_key IS NULL) AS missing
FROM dual;

SELECT 'ops_exception' AS snap, 'VEE' AS excp_source,
    (SELECT COUNT(*) FROM cisadm.d1_vee_excp) AS source_cnt,
    (SELECT COUNT(*) FROM cisadm.ops_exception_rpt_curr WHERE excp_source = 'VEE') AS snap_cnt,
    (SELECT COUNT(*) FROM cisadm.d1_vee_excp s
     LEFT JOIN cisadm.ops_exception_rpt_curr o ON o.excp_source = 'VEE' AND o.excp_natural_key = s.vee_excp_id
     WHERE o.excp_natural_key IS NULL) AS missing
FROM dual;

SELECT 'workflow_queue' AS snap, 'CI_TD_ENTRY + CI_BATCH_INST' AS physical_driver,
    (SELECT COUNT(*) FROM cisadm.ci_td_entry) AS todo_src,
    (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr WHERE queue_source = 'TODO') AS todo_snap,
    (SELECT COUNT(*) FROM cisadm.ci_batch_inst) AS batch_src,
    (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr WHERE queue_source = 'BATCH') AS batch_snap
FROM dual;

-- View enrichment coverage (nullable columns OK; population must not depend on INNER view)
SELECT 'case_prem_contact' AS snap, 'cms_ci_case_vw timing' AS enrichment,
    SUM(CASE WHEN case_cre_dttm IS NULL THEN 1 ELSE 0 END) AS null_timing_rows,
    COUNT(*) AS total_rows
FROM cisadm.case_prem_contact_rpt_curr;

SELECT 'field_activity' AS snap, 'boda appointment flag' AS enrichment,
    SUM(CASE WHEN appointment_flg IS NULL THEN 1 ELSE 0 END) AS null_appt_rows,
    COUNT(*) AS total_rows
FROM cisadm.field_activity_rpt_curr;

SELECT 'device_sp' AS snap, 'identifier overlay' AS enrichment,
    SUM(CASE WHEN utility_device_id IS NULL THEN 1 ELSE 0 END) AS null_id_rows,
    COUNT(*) AS total_rows
FROM cisadm.device_sp_rpt_curr;
