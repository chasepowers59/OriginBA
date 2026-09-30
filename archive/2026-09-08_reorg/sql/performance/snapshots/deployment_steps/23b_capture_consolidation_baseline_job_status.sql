PROMPT ============================================================
PROMPT Capture consolidation baseline job status
PROMPT ============================================================

PROMPT Consolidation one-time baseline job definitions

SELECT owner, job_name, enabled, state, job_action, start_date, next_run_date,
       failure_count, run_count, comments
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name IN (
      'JOB_BASELINE_ACCT_CUSTOMER_RPT_CURR_ONCE',
      'JOB_BASELINE_CASE_PREM_CONTACT_RPT_CURR_ONCE',
      'JOB_BASELINE_CREW_OPS_RPT_CURR_ONCE',
      'JOB_BASELINE_WO_PROC_RPT_CURR_ONCE',
      'JOB_BASELINE_SA_AGED_BAL_RPT_CURR_ONCE',
      'JOB_BASELINE_NEW_SERVICE_PIPELINE_RPT_CURR_ONCE',
      'JOB_BASELINE_FIELD_ACTIVITY_RPT_CURR_ONCE',
      'JOB_BASELINE_DEVICE_SP_RPT_CURR_ONCE',
      'JOB_BASELINE_PAY_EVENT_RPT_CURR_ONCE',
      'JOB_BASELINE_BILLABLE_CHARGE_RPT_CURR_ONCE',
      'JOB_BASELINE_WORKFLOW_QUEUE_RPT_CURR_ONCE',
      'JOB_BASELINE_OPS_EXCEPTION_RPT_CURR_ONCE'
  )
ORDER BY start_date, job_name;

PROMPT Recent consolidation baseline job run history

SELECT owner, job_name, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name IN (
      'JOB_BASELINE_ACCT_CUSTOMER_RPT_CURR_ONCE',
      'JOB_BASELINE_CASE_PREM_CONTACT_RPT_CURR_ONCE',
      'JOB_BASELINE_CREW_OPS_RPT_CURR_ONCE',
      'JOB_BASELINE_WO_PROC_RPT_CURR_ONCE',
      'JOB_BASELINE_SA_AGED_BAL_RPT_CURR_ONCE',
      'JOB_BASELINE_NEW_SERVICE_PIPELINE_RPT_CURR_ONCE',
      'JOB_BASELINE_FIELD_ACTIVITY_RPT_CURR_ONCE',
      'JOB_BASELINE_DEVICE_SP_RPT_CURR_ONCE',
      'JOB_BASELINE_PAY_EVENT_RPT_CURR_ONCE',
      'JOB_BASELINE_BILLABLE_CHARGE_RPT_CURR_ONCE',
      'JOB_BASELINE_WORKFLOW_QUEUE_RPT_CURR_ONCE',
      'JOB_BASELINE_OPS_EXCEPTION_RPT_CURR_ONCE'
  )
ORDER BY actual_start_date DESC, job_name;

PROMPT Consolidation snapshot row counts and freshness

SELECT 'customer_ops' AS workstream, 'ACCT_CUSTOMER_RPT_CURR' AS table_name,
       COUNT(*) AS live_row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.acct_customer_rpt_curr
UNION ALL SELECT 'customer_ops', 'CASE_PREM_CONTACT_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.case_prem_contact_rpt_curr
UNION ALL SELECT 'new_services', 'NEW_SERVICE_PIPELINE_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.new_service_pipeline_rpt_curr
UNION ALL SELECT 'field_ops', 'FIELD_ACTIVITY_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.field_activity_rpt_curr
UNION ALL SELECT 'field_ops', 'CREW_OPS_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.crew_ops_rpt_curr
UNION ALL SELECT 'meter_ops', 'DEVICE_SP_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.device_sp_rpt_curr
UNION ALL SELECT 'cashiering', 'PAY_EVENT_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.pay_event_rpt_curr
UNION ALL SELECT 'finance', 'BILLABLE_CHARGE_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.billable_charge_rpt_curr
UNION ALL SELECT 'debt_mgmt', 'SA_AGED_BAL_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.sa_aged_bal_rpt_curr
UNION ALL SELECT 'debt_mgmt', 'WO_PROC_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.wo_proc_rpt_curr
UNION ALL SELECT 'common', 'OPS_EXCEPTION_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.ops_exception_rpt_curr
UNION ALL SELECT 'common', 'WORKFLOW_QUEUE_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.workflow_queue_rpt_curr
ORDER BY 1, 2;
