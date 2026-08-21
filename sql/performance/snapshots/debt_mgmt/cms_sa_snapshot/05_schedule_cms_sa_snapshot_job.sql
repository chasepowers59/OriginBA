BEGIN
    BEGIN
        DBMS_SCHEDULER.DROP_JOB(
            job_name => 'CISADM.JOB_REFRESH_CMS_SA_SNAPSHOT',
            force    => TRUE
        );
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -27475 THEN
                RAISE;
            END IF;
    END;

    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_CMS_SA_SNAPSHOT',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_CMS_SA_SNAPSHOT',
        start_date      => SYSTIMESTAMP,
        repeat_interval => 'FREQ=DAILY;BYHOUR=4,10,16,22;BYMINUTE=30;BYSECOND=0',
        enabled         => TRUE,
        comments        => 'Refresh CMS SA aged-balance snapshot every 6 hours at 04:30, 10:30, 16:30, and 22:30 GMT'
    );
END;
/
