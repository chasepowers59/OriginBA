PROMPT Drop one-time BSEG_BILLED_USAGE_RPT_CURR full-history cycle-fallback refresh job.

BEGIN
    DBMS_SCHEDULER.DROP_JOB(
        job_name => 'CISADM.JOB_ONCE_FULL_BSEG_BILLED_CYCLE_FIX',
        force    => TRUE
    );
END;
/
