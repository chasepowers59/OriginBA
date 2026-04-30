PROMPT ============================================================
PROMPT Schedule initial baseline full-history refreshes
PROMPT ============================================================
PROMPT This script creates one-time DBMS_SCHEDULER jobs for the first
PROMPT full-history load. It does not wait for the jobs to finish.
PROMPT
PROMPT Intended use:
PROMPT   1. Create tables.
PROMPT   2. Deploy full-history procedures.
PROMPT   3. Run this script.
PROMPT   4. Come back later and run status capture + validation.
PROMPT
PROMPT Start offsets from current database time:
PROMPT   FT_RPT_CURR                         + 30 minutes
PROMPT   BSEG_BILLED_USAGE_RPT_CURR          + 60 minutes
PROMPT   BSEG_SQ_USAGE_RPT_CURR              + 90 minutes
PROMPT   D1_MSRMT_RPT_CURR                   + 120 minutes
PROMPT   FT_GL_DISTRIBUTION_RPT_CURR         + 150 minutes
PROMPT   D1_USAGE_RPT_CURR                   + 180 minutes
PROMPT   D1_USAGE_SCALAR_DTL_RPT_CURR        + 210 minutes

DECLARE
    PROCEDURE drop_job_if_exists(p_job_name IN VARCHAR2) IS
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(
            job_name => p_job_name,
            force    => TRUE
        );
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN
                RAISE;
            END IF;
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
    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_FT_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_FT_RPT_CURR',
        p_minutes    => 30,
        p_comments   => 'One-time initial full-history baseline load for FT_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        p_minutes    => 60,
        p_comments   => 'One-time initial full-history baseline load for BSEG_BILLED_USAGE_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        p_minutes    => 90,
        p_comments   => 'One-time initial full-history baseline load for BSEG_SQ_USAGE_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_D1_MSRMT_RPT_CURR',
        p_minutes    => 120,
        p_comments   => 'One-time initial full-history baseline load for D1_MSRMT_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        p_minutes    => 150,
        p_comments   => 'One-time initial full-history baseline load for FT_GL_DISTRIBUTION_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_D1_USAGE_RPT_CURR',
        p_minutes    => 180,
        p_comments   => 'One-time initial full-history baseline load for D1_USAGE_RPT_CURR'
    );

    create_one_time_job(
        p_job_name   => 'CISADM.JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE',
        p_job_action => 'CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        p_minutes    => 210,
        p_comments   => 'One-time initial full-history baseline load for D1_USAGE_SCALAR_DTL_RPT_CURR'
    );
END;
/

PROMPT ============================================================
PROMPT Scheduled one-time baseline jobs
PROMPT ============================================================

SELECT
    owner,
    job_name,
    enabled,
    state,
    job_action,
    start_date,
    next_run_date,
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
ORDER BY next_run_date, job_name;
