PROMPT ============================================================
PROMPT College Station TEST: pause rolling refreshes, then run all 7
PROMPT 2-year truncate+reload baselines in parallel via scheduler
PROMPT ============================================================

-- Stop/disable operational rolling jobs so they cannot write mid-truncate.
BEGIN
    FOR rec IN (
        SELECT column_value AS job_name
        FROM TABLE(sys.odcivarchar2list(
            'JOB_REFRESH_FT_RPT_CURR',
            'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
            'JOB_REFRESH_BSEG_SQ_USAGE_RPT_CURR',
            'JOB_REFRESH_D1_MSRMT_RPT_CURR',
            'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
            'JOB_REFRESH_D1_USAGE_RPT_CURR',
            'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
            'JOB_REFRESH_CMS_SA_SNAPSHOT',
            'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB'
        ))
    ) LOOP
        BEGIN
            DBMS_SCHEDULER.STOP_JOB(
                job_name => 'CISADM.' || rec.job_name,
                force    => TRUE
            );
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE NOT IN (-27366, -27475, -27476) THEN
                    RAISE;
                END IF;
        END;

        BEGIN
            DBMS_SCHEDULER.DISABLE('CISADM.' || rec.job_name, TRUE);
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE NOT IN (-27475, -27476, -27478) THEN
                    RAISE;
                END IF;
        END;
    END LOOP;
END;
/

-- Recreate one-time baseline jobs and submit all in parallel (async).
BEGIN
    FOR rec IN (
        SELECT column_value AS job_name
        FROM TABLE(sys.odcivarchar2list(
            'JOB_BASELINE_FT_RPT_CURR_ONCE',
            'JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
            'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE'
        ))
    ) LOOP
        BEGIN
            DBMS_SCHEDULER.DROP_JOB(
                job_name => 'CISADM.' || rec.job_name,
                force    => TRUE
            );
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE NOT IN (-27475, -27476) THEN
                    RAISE;
                END IF;
        END;
    END LOOP;
END;
/

BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_FT_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_MSRMT_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'College Station TEST 2yr truncate+reload baseline'
    );
END;
/

-- RUN_JOB only (do not ENABLE). ENABLE+RUN_JOB leaves the job enabled and
-- Oracle can fire a second run when the manual run completes.
BEGIN
    FOR rec IN (
        SELECT column_value AS job_name
        FROM TABLE(sys.odcivarchar2list(
            'JOB_BASELINE_FT_RPT_CURR_ONCE',
            'JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
            'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
            'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE'
        ))
    ) LOOP
        DBMS_SCHEDULER.RUN_JOB(
            job_name            => 'CISADM.' || rec.job_name,
            use_current_session => FALSE
        );
    END LOOP;
END;
/

PROMPT All 7 College Station 2yr baseline jobs submitted in parallel.
SELECT job_name, state, enabled,
       TO_CHAR(last_start_date, 'YYYY-MM-DD HH24:MI:SS') last_start
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
ORDER BY job_name;
