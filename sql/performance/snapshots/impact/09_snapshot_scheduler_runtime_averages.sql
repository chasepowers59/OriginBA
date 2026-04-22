-- Purpose:
--   Summarize observed scheduler runtime behavior for each snapshot refresh job.
--
-- Use this when:
--   - estimating refresh-window cost
--   - comparing average and worst-case runtime across snapshots
--   - documenting scheduler stability and run success rates
--
-- Notes:
--   - runtime is derived from ALL_SCHEDULER_JOB_RUN_DETAILS.RUN_DURATION
--   - results are limited to retained scheduler history

WITH job_map AS (
    SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS table_name, 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR' AS job_name FROM dual UNION ALL
    SELECT 'billing', 'BSEG_SQ_USAGE_RPT_CURR', 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB' FROM dual UNION ALL
    SELECT 'finance', 'FT_RPT_CURR', 'JOB_REFRESH_FT_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR', 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 'debt_mgmt', 'ACCT_DEBT_RPT_CURR', 'JOB_REFRESH_ACCT_DEBT_RPT_CURR' FROM dual UNION ALL
    SELECT 'debt_mgmt', 'COLL_PROC_RPT_CURR', 'JOB_REFRESH_COLL_PROC_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_RPT_CURR', 'JOB_REFRESH_D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR', 'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_MSRMT_RPT_CURR', 'JOB_REFRESH_D1_MSRMT_RPT_CURR' FROM dual UNION ALL
    SELECT 'payments_cashiering', 'PAY_TNDR_CASH_RPT_CURR', 'REFRESH_PAY_TNDR_CASH_RPT_CURR_JB' FROM dual
),
run_hist AS (
    SELECT
        j.workstream,
        j.table_name,
        j.job_name,
        r.status,
        r.actual_start_date,
        (
            EXTRACT(DAY FROM r.run_duration) * 86400 +
            EXTRACT(HOUR FROM r.run_duration) * 3600 +
            EXTRACT(MINUTE FROM r.run_duration) * 60 +
            EXTRACT(SECOND FROM r.run_duration)
        ) AS run_seconds
    FROM job_map j
    LEFT JOIN all_scheduler_job_run_details r
      ON r.owner = 'CISADM'
     AND r.job_name = j.job_name
)
SELECT
    workstream,
    table_name,
    job_name,
    COUNT(CASE WHEN actual_start_date IS NOT NULL THEN 1 END) AS observed_runs,
    COUNT(CASE WHEN status = 'SUCCEEDED' THEN 1 END) AS succeeded_runs,
    COUNT(CASE WHEN status <> 'SUCCEEDED' AND status IS NOT NULL THEN 1 END) AS non_succeeded_runs,
    ROUND(AVG(run_seconds), 2) AS avg_run_seconds,
    ROUND(MEDIAN(run_seconds), 2) AS median_run_seconds,
    ROUND(MAX(run_seconds), 2) AS max_run_seconds,
    MIN(actual_start_date) AS oldest_observed_run,
    MAX(actual_start_date) AS latest_observed_run
FROM run_hist
GROUP BY
    workstream,
    table_name,
    job_name
ORDER BY
    avg_run_seconds DESC NULLS LAST,
    max_run_seconds DESC NULLS LAST;
