-- Purpose:
--   Review scheduler job definitions and recent run history for snapshot refreshes.

-- 4a) Current snapshot refresh job definitions
SELECT
    owner,
    job_name,
    enabled,
    state,
    job_action,
    repeat_interval,
    last_start_date,
    next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND (
        UPPER(job_action) LIKE 'CISADM.REFRESH%RPT_CURR%'
     OR UPPER(job_name) LIKE '%RPT_CURR%'
      )
ORDER BY
    job_name;

-- 4b) Recent run history
SELECT
    owner,
    job_name,
    status,
    actual_start_date,
    run_duration,
    additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND (
        UPPER(job_name) LIKE '%RPT_CURR%'
      )
ORDER BY
    actual_start_date DESC
FETCH FIRST 100 ROWS ONLY;
