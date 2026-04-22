BEGIN
    DBMS_SCHEDULER.create_job (
        job_name        => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=2,8,14,20;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh billed usage determinant snapshot every 6 hours at 02:00, 08:00, 14:00, and 20:00 GMT'
    );
END;
/
