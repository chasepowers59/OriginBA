BEGIN
    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=1,7,13,19;BYMINUTE=30;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh bill-segment billed usage snapshot every 6 hours at 01:30, 07:30, 13:30, and 19:30 GMT'
    );
END;
/
