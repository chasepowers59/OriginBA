-- Extended null / coverage audit for all 12 consolidation snapshots on demo.
-- Run after refresh via scripts/local/run_consolidation_snapshot_demo_qa.sh

-- ACCT_CUSTOMER_RPT_CURR
SELECT 'ACCT_CUSTOMER_RPT_CURR' AS snapshot_name, 'code_desc_audit' AS audit_type,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND NULLIF(TRIM(bill_cyc_cd), '') IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND NULLIF(TRIM(cust_cl_cd), '') IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.acct_customer_rpt_curr;

-- CASE_PREM_CONTACT_RPT_CURR
SELECT 'CASE_PREM_CONTACT_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN case_status_desc IS NULL AND case_status_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN prem_type_desc IS NULL AND prem_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN prem_address1 IS NULL AND prem_id IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.case_prem_contact_rpt_curr;

-- NEW_SERVICE_PIPELINE_RPT_CURR
SELECT 'NEW_SERVICE_PIPELINE_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN ft_bal_cur_amt IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.new_service_pipeline_rpt_curr;

-- FIELD_ACTIVITY_RPT_CURR
SELECT 'FIELD_ACTIVITY_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN activity_type_desc IS NULL AND activity_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN acct_customer_name IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.field_activity_rpt_curr;

-- CREW_OPS_RPT_CURR
SELECT 'CREW_OPS_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN crew_type_desc IS NULL AND crew_type_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN fa_activity_count IS NULL THEN 1 ELSE 0 END)
FROM cisadm.crew_ops_rpt_curr;

-- DEVICE_SP_RPT_CURR
SELECT 'DEVICE_SP_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN device_type_desc IS NULL AND device_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN us_type_desc IS NULL AND us_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN d1_sp_id IS NULL AND currently_installed_sw = 'Y' THEN 1 ELSE 0 END)
FROM cisadm.device_sp_rpt_curr;

-- PAY_EVENT_RPT_CURR
SELECT 'PAY_EVENT_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN pay_status_desc IS NULL AND pay_status_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN pay_amt IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.pay_event_rpt_curr;

-- BILLABLE_CHARGE_RPT_CURR
SELECT 'BILLABLE_CHARGE_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN billable_chg_stat_desc IS NULL AND billable_chg_stat IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN sa_id IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN charge_amt IS NULL THEN 1 ELSE 0 END)
FROM cisadm.billable_charge_rpt_curr;

-- SA_AGED_BAL_RPT_CURR
SELECT 'SA_AGED_BAL_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN total_debt IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.sa_aged_bal_rpt_curr;

-- WO_PROC_RPT_CURR
SELECT 'WO_PROC_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN wo_status_desc IS NULL AND wo_status_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN wo_sa_count IS NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN acct_id IS NULL THEN 1 ELSE 0 END)
FROM cisadm.wo_proc_rpt_curr;

-- OPS_EXCEPTION_RPT_CURR
SELECT 'OPS_EXCEPTION_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN excp_severity_desc IS NULL AND excp_severity_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN bseg_excp_desc IS NULL AND bseg_excp_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN excp_natural_key IS NULL THEN 1 ELSE 0 END)
FROM cisadm.ops_exception_rpt_curr;

-- WORKFLOW_QUEUE_RPT_CURR (TODO FK coverage)
SELECT 'WORKFLOW_QUEUE_RPT_CURR', 'todo_fk_coverage',
    COUNT(*),
    SUM(CASE WHEN fk_acct_id IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN fk_sa_id IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN fk_prem_id IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.workflow_queue_rpt_curr
WHERE queue_source = 'TODO';

SELECT 'WORKFLOW_QUEUE_RPT_CURR', 'code_desc_audit',
    COUNT(*),
    SUM(CASE WHEN td_type_desc IS NULL AND td_type_cd IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN entry_status_desc IS NULL AND entry_status_flg IS NOT NULL THEN 1 ELSE 0 END),
    SUM(CASE WHEN queue_source IS NULL OR queue_natural_key IS NULL THEN 1 ELSE 0 END)
FROM cisadm.workflow_queue_rpt_curr;
