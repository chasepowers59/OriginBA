BEGIN
    DBMS_SCHEDULER.CREATE_JOB (
        job_name        => 'CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR_JB',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=6;BYMINUTE=0;BYSECOND=0',
        -- Fixed-time alternative:
        -- repeat_interval => 'FREQ=DAILY;BYHOUR=7,12;BYMINUTE=0;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refreshes PAY_TNDR_CASH_RPT_CURR daily at 6:00 AM'
        -- Fixed-time alternative comment:
        -- comments        => 'Refreshes PAY_TNDR_CASH_RPT_CURR daily at 7:00 AM and 12:00 PM'
    );
END;
/
