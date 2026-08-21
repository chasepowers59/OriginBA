PROMPT Schedule one-time BSEG_BILLED_USAGE_RPT_CURR full-history cycle-fallback refresh.

BEGIN
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(
            job_name => 'CISADM.JOB_ONCE_FULL_BSEG_BILLED_CYCLE_FIX',
            force    => TRUE
        );
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN
                RAISE;
            END IF;
    END;

    DBMS_SCHEDULER.CREATE_JOB(
        job_name   => 'CISADM.JOB_ONCE_FULL_BSEG_BILLED_CYCLE_FIX',
        job_type   => 'STORED_PROCEDURE',
        job_action => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        start_date => SYSTIMESTAMP,
        enabled    => TRUE,
        auto_drop  => FALSE,
        comments   => 'One-time full refresh to backfill bill cycle fallback after procedure update'
    );
END;
/
