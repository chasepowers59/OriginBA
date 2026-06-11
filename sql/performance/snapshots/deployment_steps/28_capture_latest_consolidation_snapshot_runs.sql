PROMPT ============================================================
PROMPT Capture latest consolidation snapshot scheduler runs
PROMPT ============================================================

SELECT job_name, status, actual_start_date, run_duration, additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name IN (
      'JOB_REFRESH_ACCT_CUSTOMER_RPT_CURR',
      'JOB_REFRESH_CASE_PREM_CONTACT_RPT_CURR',
      'JOB_REFRESH_NEW_SERVICE_PIPELINE_RPT_CURR',
      'JOB_REFRESH_FIELD_ACTIVITY_RPT_CURR',
      'JOB_REFRESH_CREW_OPS_RPT_CURR',
      'JOB_REFRESH_DEVICE_SP_RPT_CURR',
      'JOB_REFRESH_PAY_EVENT_RPT_CURR',
      'JOB_REFRESH_BILLABLE_CHARGE_RPT_CURR',
      'JOB_REFRESH_SA_AGED_BAL_RPT_CURR',
      'JOB_REFRESH_WO_PROC_RPT_CURR',
      'JOB_REFRESH_OPS_EXCEPTION_RPT_CURR',
      'JOB_REFRESH_WORKFLOW_QUEUE_RPT_CURR'
  )
ORDER BY actual_start_date DESC, job_name
FETCH FIRST 48 ROWS ONLY;
