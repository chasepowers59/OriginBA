BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_MSRMT_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=2,8,14,20;BYMINUTE=30;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh final measurement reporting snapshot every 6 hours at 02:30, 08:30, 14:30, and 20:30 GMT'
    );
END;
/
