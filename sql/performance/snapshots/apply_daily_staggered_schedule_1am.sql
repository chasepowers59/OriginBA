-- Purpose:
--   Reconfigure the active governed snapshot refresh jobs to run once daily
--   in a staggered morning window starting at 01:00.
--
-- Notes:
--   - Times below assume the scheduler timezone shown by the job views.
--   - Based on the observed job output captured on 2026-04-20, that timezone is GMT.
--   - With 30-minute spacing, a small overlap between the two longest meter-ops jobs
--     remains unavoidable, so the longest jobs are placed at the end of the window.

BEGIN
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=1;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh FT header snapshot daily at 01:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=1;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh bill-segment billed usage snapshot daily at 01:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=2;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        attribute => 'comments',
        value     => 'Refresh billed usage determinant snapshot daily at 02:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=2;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh final measurement reporting snapshot daily at 02:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=3;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh FT GL distribution snapshot daily at 03:00 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=3;BYMINUTE=30;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh usage header snapshot daily at 03:30 GMT'
    );

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        attribute => 'repeat_interval',
        value     => 'FREQ=DAILY;BYHOUR=4;BYMINUTE=0;BYSECOND=0'
    );
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name      => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        attribute => 'comments',
        value     => 'Refresh D1 usage scalar-detail reporting snapshot daily at 04:00 GMT'
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
