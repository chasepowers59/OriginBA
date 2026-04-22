BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=3,9,15,21;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh FT GL distribution snapshot every 6 hours at 03:00, 09:00, 15:00, and 21:00 GMT'
    );
END;
/
