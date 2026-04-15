BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh FT header snapshot every 6 hours'
    );
END;
/
