BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_COLL_PROC_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_COLL_PROC_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        -- Fixed-time alternative:
        -- repeat_interval => 'FREQ=DAILY;BYHOUR=7,12;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh collection process snapshot every 6 hours'
        -- Fixed-time alternative comment:
        -- comments        => 'Refresh collection process snapshot daily at 7:00 AM and 12:00 PM'
    );
END;
/
