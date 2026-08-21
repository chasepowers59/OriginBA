-- Purpose:
--   Return the most recent observed scheduler run for the active 7 governed
--   snapshot jobs plus CMS_SA_SNAPSHOT domain support.
--
-- Use this when:
--   - capturing current refresh durations for operational tracking
--   - updating schedule documents with the latest observed runtime
--   - comparing before/after runtime changes after procedure tuning

WITH job_map AS (
    SELECT 1 AS sort_order, 'finance' AS workstream, 'FT_RPT_CURR' AS table_name, 'JOB_REFRESH_FT_RPT_CURR' AS job_name FROM dual UNION ALL
    SELECT 2, 'billing', 'BSEG_BILLED_USAGE_RPT_CURR', 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 3, 'billing', 'BSEG_SQ_USAGE_RPT_CURR', 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB' FROM dual UNION ALL
    SELECT 4, 'meter_ops', 'D1_MSRMT_RPT_CURR', 'JOB_REFRESH_D1_MSRMT_RPT_CURR' FROM dual UNION ALL
    SELECT 5, 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR', 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 6, 'meter_ops', 'D1_USAGE_RPT_CURR', 'JOB_REFRESH_D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 7, 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR', 'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 8, 'debt_mgmt', 'CMS_SA_SNAPSHOT', 'JOB_REFRESH_CMS_SA_SNAPSHOT' FROM dual
),
run_hist AS (
    SELECT
        j.sort_order,
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
    ROUND(h.run_seconds, 0) AS run_seconds,
    ROUND(h.run_seconds / 60, 2) AS run_minutes,
    j.next_run_date
FROM run_hist h
LEFT JOIN all_scheduler_jobs j
  ON j.owner = 'CISADM'
 AND j.job_name = h.job_name
WHERE h.rn = 1
ORDER BY h.sort_order;
