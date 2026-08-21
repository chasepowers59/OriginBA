PROMPT ============================================================
PROMPT Run all 8 full-history baselines in 3 throttled streams
PROMPT (PROD-safe: max 3 concurrent sessions instead of 8)
PROMPT Stream A: FT -> FT_GL -> CMS_SA
PROMPT Stream B: BSEG_BILLED -> BSEG_SQ
PROMPT Stream C: D1_USAGE -> D1_USAGE_SCALAR -> D1_MSRMT
PROMPT ============================================================

BEGIN
    FOR rec IN (
        SELECT column_value AS job_name
        FROM TABLE(sys.odcivarchar2list(
            'JOB_BASELINE_STREAM_A_ONCE',
            'JOB_BASELINE_STREAM_B_ONCE',
            'JOB_BASELINE_STREAM_C_ONCE'
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
        job_name   => 'CISADM.JOB_BASELINE_STREAM_A_ONCE',
        job_type   => 'PLSQL_BLOCK',
        job_action => q'[
            BEGIN
                cisadm.refresh_ft_rpt_curr;
                cisadm.refresh_ft_gl_distribution_rpt_curr;
                cisadm.refresh_cms_sa_snapshot;
            END;]',
        enabled    => FALSE,
        auto_drop  => FALSE,
        comments   => 'Baseline stream A: FT, FT_GL, CMS_SA (serial)'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name   => 'CISADM.JOB_BASELINE_STREAM_B_ONCE',
        job_type   => 'PLSQL_BLOCK',
        job_action => q'[
            BEGIN
                cisadm.refresh_bseg_billed_usage_rpt_curr;
                cisadm.refresh_bseg_sq_usage_rpt_curr;
            END;]',
        enabled    => FALSE,
        auto_drop  => FALSE,
        comments   => 'Baseline stream B: BSEG_BILLED, BSEG_SQ (serial)'
    );
    DBMS_SCHEDULER.CREATE_JOB(
        job_name   => 'CISADM.JOB_BASELINE_STREAM_C_ONCE',
        job_type   => 'PLSQL_BLOCK',
        job_action => q'[
            BEGIN
                cisadm.refresh_d1_usage_rpt_curr;
                cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
                cisadm.refresh_d1_msrmt_rpt_curr;
            END;]',
        enabled    => FALSE,
        auto_drop  => FALSE,
        comments   => 'Baseline stream C: D1_USAGE, SCALAR, D1_MSRMT (serial)'
    );
END;
/

BEGIN
    FOR rec IN (
        SELECT column_value AS job_name
        FROM TABLE(sys.odcivarchar2list(
            'JOB_BASELINE_STREAM_A_ONCE',
            'JOB_BASELINE_STREAM_B_ONCE',
            'JOB_BASELINE_STREAM_C_ONCE'
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

PROMPT All 3 baseline streams submitted.
SELECT job_name, state, enabled
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name LIKE 'JOB_BASELINE_STREAM_%_ONCE'
ORDER BY job_name;
