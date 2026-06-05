-- Install gate: baseline one-time jobs must have completed successfully.
-- Returns rows only when something is wrong (empty result set = pass).

WITH expected_jobs AS (
    SELECT 'JOB_BASELINE_FT_RPT_CURR_ONCE' AS job_name FROM dual
    UNION ALL SELECT 'JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE' FROM dual
    UNION ALL SELECT 'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE' FROM dual
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
    INNER JOIN expected_jobs e
        ON e.job_name = d.job_name
    WHERE d.owner = 'CISADM'
)
SELECT
    e.job_name,
    'BASELINE_JOB_NOT_SUCCEEDED' AS failure_code,
    NVL(l.status, 'NO_RUN_HISTORY') AS detail
FROM expected_jobs e
LEFT JOIN latest_run l
    ON l.job_name = e.job_name
   AND l.rn = 1
WHERE l.status IS NULL
   OR l.status <> 'SUCCEEDED'
