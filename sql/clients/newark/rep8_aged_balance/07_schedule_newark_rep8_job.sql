-- Nightly scheduler for Newark REP8 staging refresh (Newark-only).

PROMPT Scheduling CISADM.JOB_REFRESH_NEWARK_REP8_AGED_BALANCE...

BEGIN
    BEGIN
        DBMS_SCHEDULER.DROP_JOB('CISADM.JOB_REFRESH_NEWARK_REP8_AGED_BALANCE', TRUE);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE NOT IN (-27475, -27476) THEN
                RAISE;
            END IF;
    END;

    DBMS_SCHEDULER.CREATE_JOB(
        job_name        => 'CISADM.JOB_REFRESH_NEWARK_REP8_AGED_BALANCE',
        job_type        => 'STORED_PROCEDURE',
        job_action      => 'CISADM.REFRESH_NEWARK_REP8_AGED_BALANCE',
        start_date      => TRUNC(SYSDATE) + 1 + INTERVAL '2' HOUR,
        repeat_interval => 'FREQ=DAILY;BYHOUR=2;BYMINUTE=0',
        enabled         => FALSE,
        auto_drop       => FALSE,
        comments        => 'Newark REP8 aged balance nightly staging refresh'
    );
END;
/

PROMPT Job created DISABLED. Enable after first successful manual refresh:
PROMPT   EXEC DBMS_SCHEDULER.ENABLE('CISADM.JOB_REFRESH_NEWARK_REP8_AGED_BALANCE');
