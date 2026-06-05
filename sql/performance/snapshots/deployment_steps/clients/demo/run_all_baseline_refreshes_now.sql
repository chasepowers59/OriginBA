PROMPT ============================================================
PROMPT Demo: disable staggered baseline scheduler jobs
PROMPT ============================================================
BEGIN
    FOR rec IN (
        SELECT job_name
        FROM all_scheduler_jobs
        WHERE owner = 'CISADM'
          AND job_name LIKE 'JOB_BASELINE_%'
    ) LOOP
        BEGIN
            DBMS_SCHEDULER.DISABLE('CISADM.' || rec.job_name, TRUE);
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE NOT IN (-27475, -27476) THEN
                    RAISE;
                END IF;
        END;
    END LOOP;
END;
/

PROMPT ============================================================
PROMPT Demo: run all 7 full-history baseline refreshes now (sequential)
PROMPT ============================================================

PROMPT [1/7] FT_RPT_CURR
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

PROMPT [4/7] D1_MSRMT_RPT_CURR
BEGIN
    cisadm.refresh_d1_msrmt_rpt_curr;
END;
/

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/

PROMPT [6/7] D1_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/
