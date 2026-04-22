-- Purpose:
--   Reconfigure the active governed snapshot refresh jobs to keep the
--   current 01:00 base-time stagger but repeat every 6 hours.
--
-- Notes:
--   - Times below assume the scheduler timezone shown by the job views.
--   - Based on the observed job output captured in this project, that timezone is GMT.
--   - This keeps the existing half-hour staggering while restoring the
--     6-hour cadence across the day.

BEGIN
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=1,7,13,19;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh FT header snapshot every 6 hours at 01:00, 07:00, 13:00, and 19:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=1,7,13,19;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh bill-segment billed usage snapshot every 6 hours at 01:30, 07:30, 13:30, and 19:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=2,8,14,20;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        attribute => 'comments',
        value     => 'Refresh billed usage determinant snapshot every 6 hours at 02:00, 08:00, 14:00, and 20:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=2,8,14,20;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh final measurement reporting snapshot every 6 hours at 02:30, 08:30, 14:30, and 20:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=3,9,15,21;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh FT GL distribution snapshot every 6 hours at 03:00, 09:00, 15:00, and 21:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=3,9,15,21;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh usage header snapshot every 6 hours at 03:30, 09:30, 15:30, and 21:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=4,10,16,22;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh D1 usage scalar-detail reporting snapshot every 6 hours at 04:00, 10:00, 16:00, and 22:00 GMT'
    );
END;
/

SELECT owner,
       job_name,
       enabled,
       state,
       repeat_interval,
       next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name IN (
        'JOB_REFRESH_FT_RPT_CURR',
        'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        'JOB_REFRESH_D1_MSRMT_RPT_CURR',
        'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        'JOB_REFRESH_D1_USAGE_RPT_CURR',
        'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR'
      )
ORDER BY next_run_date, job_name;
