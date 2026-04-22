BEGIN
    DBMS_SCHEDULER.CREATE_JOB (
        job_name        => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=4,10,16,22;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh D1 usage scalar-detail reporting snapshot every 6 hours at 04:00, 10:00, 16:00, and 22:00 GMT'
    );
END;
/
