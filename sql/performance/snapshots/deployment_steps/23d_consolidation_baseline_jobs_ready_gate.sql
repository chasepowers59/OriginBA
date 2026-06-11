-- Install gate: consolidation baseline one-time jobs must have completed successfully.
-- Returns rows only when something is wrong (empty result set = pass).

WITH expected_jobs AS (
    SELECT 'JOB_BASELINE_ACCT_CUSTOMER_RPT_CURR_ONCE' AS job_name FROM dual
    UNION ALL SELECT 'JOB_BASELINE_CASE_PREM_CONTACT_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_CREW_OPS_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_WO_PROC_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_SA_AGED_BAL_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_NEW_SERVICE_PIPELINE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_FIELD_ACTIVITY_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_DEVICE_SP_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_PAY_EVENT_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_BILLABLE_CHARGE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_WORKFLOW_QUEUE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_OPS_EXCEPTION_RPT_CURR_ONCE' FROM dual
),
latest_run AS (
    SELECT
        d.job_name,
        d.status,
        d.actual_start_date,
        d.run_duration,
        ROW_NUMBER() OVER (
            PARTITION BY d.job_name
            ORDER BY d.actual_start_date DESC NULLS LAST, d.log_id DESC
        ) AS rn
    FROM all_scheduler_job_run_details d
    INNER JOIN expected_jobs e ON e.job_name = d.job_name
    WHERE d.owner = 'CISADM'
)
SELECT e.job_name, 'BASELINE_JOB_NOT_SUCCEEDED' AS failure_code,
       NVL(l.status, 'NO_RUN_HISTORY') AS detail
FROM expected_jobs e
LEFT JOIN latest_run l ON l.job_name = e.job_name AND l.rn = 1
WHERE l.status IS NULL OR l.status <> 'SUCCEEDED';
