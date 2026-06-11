PROMPT ============================================================
PROMPT Schedule consolidation baseline full-history refreshes
PROMPT ============================================================
PROMPT One-time DBMS_SCHEDULER jobs, staggered every 15 minutes.
PROMPT Heavy snapshots (WORKFLOW_QUEUE, OPS_EXCEPTION) run last.

DECLARE
    PROCEDURE drop_job_if_exists(p_job_name IN VARCHAR2) IS
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(job_name => p_job_name, force => TRUE);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN RAISE; END IF;
    END;

    PROCEDURE create_one_time_job(
        p_job_name   IN VARCHAR2,
        p_job_action IN VARCHAR2,
        p_minutes    IN NUMBER,
        p_comments   IN VARCHAR2
    ) IS
    BEGIN
        drop_job_if_exists(p_job_name);
        DBMS_SCHEDULER.CREATE_JOB(
            job_name        => p_job_name,
            job_type        => 'STORED_PROCEDURE',
            job_action      => p_job_action,
            start_date      => SYSTIMESTAMP + NUMTODSINTERVAL(p_minutes, 'MINUTE'),
            repeat_interval => NULL,
            enabled         => TRUE,
            auto_drop       => FALSE,
            comments        => p_comments
        );
    END;
BEGIN
    create_one_time_job('CISADM.JOB_BASELINE_ACCT_CUSTOMER_RPT_CURR_ONCE',
        'CISADM.REFRESH_ACCT_CUSTOMER_RPT_CURR', 0,
        'One-time full-history baseline for ACCT_CUSTOMER_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_CASE_PREM_CONTACT_RPT_CURR_ONCE',
        'CISADM.REFRESH_CASE_PREM_CONTACT_RPT_CURR', 15,
        'One-time full-history baseline for CASE_PREM_CONTACT_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_CREW_OPS_RPT_CURR_ONCE',
        'CISADM.REFRESH_CREW_OPS_RPT_CURR', 30,
        'One-time full-history baseline for CREW_OPS_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_WO_PROC_RPT_CURR_ONCE',
        'CISADM.REFRESH_WO_PROC_RPT_CURR', 45,
        'One-time full-history baseline for WO_PROC_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_SA_AGED_BAL_RPT_CURR_ONCE',
        'CISADM.REFRESH_SA_AGED_BAL_RPT_CURR', 60,
        'One-time full-history baseline for SA_AGED_BAL_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_NEW_SERVICE_PIPELINE_RPT_CURR_ONCE',
        'CISADM.REFRESH_NEW_SERVICE_PIPELINE_RPT_CURR', 75,
        'One-time full-history baseline for NEW_SERVICE_PIPELINE_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_FIELD_ACTIVITY_RPT_CURR_ONCE',
        'CISADM.REFRESH_FIELD_ACTIVITY_RPT_CURR', 90,
        'One-time full-history baseline for FIELD_ACTIVITY_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_DEVICE_SP_RPT_CURR_ONCE',
        'CISADM.REFRESH_DEVICE_SP_RPT_CURR', 105,
        'One-time full-history baseline for DEVICE_SP_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_PAY_EVENT_RPT_CURR_ONCE',
        'CISADM.REFRESH_PAY_EVENT_RPT_CURR', 120,
        'One-time full-history baseline for PAY_EVENT_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_BILLABLE_CHARGE_RPT_CURR_ONCE',
        'CISADM.REFRESH_BILLABLE_CHARGE_RPT_CURR', 135,
        'One-time full-history baseline for BILLABLE_CHARGE_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_WORKFLOW_QUEUE_RPT_CURR_ONCE',
        'CISADM.REFRESH_WORKFLOW_QUEUE_RPT_CURR', 150,
        'One-time full-history baseline for WORKFLOW_QUEUE_RPT_CURR');
    create_one_time_job('CISADM.JOB_BASELINE_OPS_EXCEPTION_RPT_CURR_ONCE',
        'CISADM.REFRESH_OPS_EXCEPTION_RPT_CURR', 165,
        'One-time full-history baseline for OPS_EXCEPTION_RPT_CURR');
END;
/

PROMPT Scheduled consolidation baseline jobs

SELECT owner, job_name, enabled, state, job_action, start_date, next_run_date, comments
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
ORDER BY next_run_date, job_name;
