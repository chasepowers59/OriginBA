-- Purpose:
--   Show the latest observed scheduler runs for each governed snapshot job
--   and a cross-job timeline of the most recent snapshot refresh executions.
--
-- Use this when:
--   - identifying which snapshot jobs ran most recently
--   - capturing actual start times and run durations before deeper testing
--   - checking whether the active refresh sequence matches expectations
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
        r.log_id,
        r.status,
        r.actual_start_date,
        r.run_duration,
        r.additional_info,
        (
            EXTRACT(DAY FROM r.run_duration) * 86400 +
            EXTRACT(HOUR FROM r.run_duration) * 3600 +
            EXTRACT(MINUTE FROM r.run_duration) * 60 +
            EXTRACT(SECOND FROM r.run_duration)
        ) AS run_seconds,
        ROW_NUMBER() OVER (
            PARTITION BY j.job_name
            ORDER BY r.actual_start_date DESC NULLS LAST, r.log_id DESC
        ) AS rn
    FROM job_map j
    LEFT JOIN all_scheduler_job_run_details r
      ON r.owner = 'CISADM'
     AND r.job_name = j.job_name
)
-- 14a) Latest observed run for each snapshot refresh job
SELECT
    h.workstream,
    h.table_name,
    h.job_name,
    j.enabled,
    j.state,
    j.repeat_interval,
    h.log_id,
    h.status,
    h.actual_start_date,
    h.run_duration,
    ROUND(h.run_seconds, 2) AS run_seconds,
    ROUND(h.run_seconds / 60, 2) AS run_minutes,
    j.next_run_date,
    h.additional_info
FROM run_hist h
LEFT JOIN all_scheduler_jobs j
  ON j.owner = 'CISADM'
 AND j.job_name = h.job_name
WHERE h.rn = 1
ORDER BY
    h.actual_start_date DESC NULLS LAST,
    h.job_name;

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
)
-- 14b) Most recent snapshot refresh runs across the full job family
SELECT
    j.workstream,
    j.table_name,
    r.job_name,
    r.log_id,
    r.status,
    r.actual_start_date,
    r.run_duration,
    ROUND(
        EXTRACT(DAY FROM r.run_duration) * 86400 +
        EXTRACT(HOUR FROM r.run_duration) * 3600 +
        EXTRACT(MINUTE FROM r.run_duration) * 60 +
        EXTRACT(SECOND FROM r.run_duration),
        2
    ) AS run_seconds,
    ROUND(
        (
            EXTRACT(DAY FROM r.run_duration) * 86400 +
            EXTRACT(HOUR FROM r.run_duration) * 3600 +
            EXTRACT(MINUTE FROM r.run_duration) * 60 +
            EXTRACT(SECOND FROM r.run_duration)
        ) / 60,
        2
    ) AS run_minutes,
    r.additional_info
FROM job_map j
JOIN all_scheduler_job_run_details r
  ON r.owner = 'CISADM'
 AND r.job_name = j.job_name
ORDER BY
    r.actual_start_date DESC,
    r.log_id DESC
FETCH FIRST 30 ROWS ONLY;
