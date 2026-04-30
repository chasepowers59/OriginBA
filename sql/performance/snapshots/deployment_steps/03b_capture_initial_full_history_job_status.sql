PROMPT ============================================================
PROMPT Capture initial baseline full-history job status
PROMPT ============================================================

PROMPT Current one-time baseline job definitions

SELECT
    owner,
    job_name,
    enabled,
    state,
    job_action,
    start_date,
    next_run_date,
    failure_count,
    run_count,
    comments
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name IN (
      'JOB_BASELINE_FT_RPT_CURR_ONCE',
      'JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
      'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE'
  )
ORDER BY start_date, job_name;

PROMPT
PROMPT Recent one-time baseline job run history

SELECT
    owner,
    job_name,
    status,
    actual_start_date,
    run_duration,
    additional_info
FROM all_scheduler_job_run_details
WHERE owner = 'CISADM'
  AND job_name IN (
      'JOB_BASELINE_FT_RPT_CURR_ONCE',
      'JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
      'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
      'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE'
  )
ORDER BY actual_start_date DESC, job_name;

PROMPT
PROMPT Active 7 snapshot row counts and freshness after baseline jobs

SELECT 'billing' AS workstream,
       'BSEG_BILLED_USAGE_RPT_CURR' AS table_name,
       COUNT(*) AS live_row_count,
       MIN(load_dttm) AS min_load_dttm,
       MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'billing',
       'BSEG_SQ_USAGE_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'finance',
       'FT_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'finance',
       'FT_GL_DISTRIBUTION_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'meter_ops',
       'D1_USAGE_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'meter_ops',
       'D1_USAGE_SCALAR_DTL_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL
SELECT 'meter_ops',
       'D1_MSRMT_RPT_CURR',
       COUNT(*),
       MIN(load_dttm),
       MAX(load_dttm)
FROM cisadm.d1_msrmt_rpt_curr;
