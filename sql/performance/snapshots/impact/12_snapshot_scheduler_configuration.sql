-- 2026-09-08: ACCT_DEBT, COLL_PROC and PAY_TNDR_CASH removed from the list (archived; not part of the active-8).
-- Purpose:
--   Review configured scheduler cadence and current scheduler state for each snapshot
--   refresh job.
--
-- Use this when:
--   - documenting intended refresh cadence
--   - checking whether jobs are enabled and scheduled
--   - verifying next-run planning for release readiness

WITH job_map AS (
    SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS table_name, 'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR' AS job_name FROM dual UNION ALL
    SELECT 'billing', 'BSEG_SQ_USAGE_RPT_CURR', 'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB' FROM dual UNION ALL
    SELECT 'finance', 'FT_RPT_CURR', 'JOB_REFRESH_FT_RPT_CURR' FROM dual UNION ALL
    SELECT 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR', 'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_RPT_CURR', 'JOB_REFRESH_D1_USAGE_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR', 'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR' FROM dual UNION ALL
    SELECT 'meter_ops', 'D1_MSRMT_RPT_CURR', 'JOB_REFRESH_D1_MSRMT_RPT_CURR' FROM dual
)
SELECT
    m.workstream,
    m.table_name,
    j.job_name,
    j.enabled,
    j.state,
    j.repeat_interval,
    j.last_start_date,
    j.next_run_date
FROM job_map m
LEFT JOIN all_scheduler_jobs j
  ON j.owner = 'CISADM'
 AND j.job_name = m.job_name
ORDER BY m.workstream, m.table_name;
