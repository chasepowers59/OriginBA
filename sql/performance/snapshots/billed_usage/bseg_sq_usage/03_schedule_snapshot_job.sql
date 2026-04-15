BEGIN
    DBMS_SCHEDULER.create_job (
        job_name        => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=HOURLY;INTERVAL=6',
        enabled         => TRUE,
        comments        => 'Refresh billed usage determinant snapshot every 6 hours'
    );
END;
/
