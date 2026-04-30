BEGIN
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(
            job_name => 'CISADM.JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
            force    => TRUE
        );
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN
                RAISE;
            END IF;
    END;

    DBMS_SCHEDULER.CREATE_JOB(
        job_name   => 'CISADM.JOB_BASELINE_BSEG_BILLED_USAGE_RPT_CURR_ONCE',
        job_type   => 'PLSQL_BLOCK',
        job_action => 'BEGIN cisadm.refresh_bseg_billed_usage_rpt_curr; END;',
        start_date => SYSTIMESTAMP + INTERVAL '120' MINUTE,
        enabled    => TRUE,
        auto_drop  => FALSE,
        comments   => 'Retry batched one-time baseline load for BSEG_BILLED_USAGE_RPT_CURR after TEMP exhaustion.'
    );
END;
/
