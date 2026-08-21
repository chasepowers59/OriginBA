PROMPT ============================================================
PROMPT Run all 7 full-history baselines in parallel (no stagger)
PROMPT Plus CMS_SA_SNAPSHOT refresh in parallel
PROMPT ============================================================

-- Create/replace one-time baseline jobs, then RUN_JOB async for all.
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
            'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE',
            'JOB_BASELINE_CMS_SA_SNAPSHOT_ONCE'
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
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_MSRMT_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time full-history baseline'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_BASELINE_CMS_SA_SNAPSHOT_ONCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_CMS_SA_SNAPSHOT',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'One-time CMS SA snapshot baseline'
    );
END;
/

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
            'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE',
            'JOB_BASELINE_CMS_SA_SNAPSHOT_ONCE'
        ))
    ) LOOP
        -- RUN_JOB only (do not ENABLE) to avoid a second scheduled fire after completion.
        DBMS_SCHEDULER.RUN_JOB(
            job_name            => 'CISADM.' || rec.job_name,
            use_current_session => FALSE
        );
    END LOOP;
END;
/

PROMPT All baseline jobs submitted in parallel.
SELECT job_name, state, enabled
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name LIKE 'JOB_BASELINE_%_ONCE'
ORDER BY job_name;
