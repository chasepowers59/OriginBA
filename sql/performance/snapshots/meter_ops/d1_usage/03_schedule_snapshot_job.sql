BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=3,9,15,21;BYMINUTE=30;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh usage header snapshot every 6 hours at 03:30, 09:30, 15:30, and 21:30 GMT'
    );
END;
/
