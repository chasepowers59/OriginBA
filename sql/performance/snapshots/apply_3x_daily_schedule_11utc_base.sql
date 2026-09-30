-- Purpose:
--   Active-8 snapshot jobs: 2 runs per day (10 and 16 UTC only — no late-evening wave),
--   30-minute stagger within each wave, faster jobs first and heaviest last.
--
-- Scheduler timezone (observed on SmartCity): GMT / UTC.
-- Wave anchors: 10:00 UTC ≈ 05:00 US Central (CDT); 16:00 UTC ≈ 11:00 AM Central (CDT).
--
-- Morning wave (10:00–13:30 UTC):
--   10:00 FT_RPT | 10:30 BSEG_BILLED | 11:00 BSEG_SQ | 11:30 D1_MSRMT
--   12:00 D1_USAGE | 12:30 CMS_SA | 13:00 FT_GL | 13:30 D1_SCALAR
-- Afternoon wave (16:00–19:30 UTC): same stagger pattern.

BEGIN
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_FT_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=10,16;BYMINUTE=0;BYSECOND=0');
    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_FT_RPT_CURR', attribute => 'comments',
        value => 'FT header snapshot 2x daily (10/16 UTC) :00 — fast first');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=10,16;BYMINUTE=30;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=11,17;BYMINUTE=0;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_D1_MSRMT_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=11,17;BYMINUTE=30;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_D1_USAGE_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=12,18;BYMINUTE=0;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_CMS_SA_SNAPSHOT', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=12,18;BYMINUTE=30;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=13,19;BYMINUTE=0;BYSECOND=0');

    DBMS_SCHEDULER.SET_ATTRIBUTE(
        name => 'CISADM.JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR', attribute => 'repeat_interval',
        value => 'FREQ=DAILY;BYHOUR=13,19;BYMINUTE=30;BYSECOND=0');
END;
/

SELECT job_name, enabled, repeat_interval, next_run_date
FROM all_scheduler_jobs
WHERE owner = 'CISADM'
  AND job_name IN (
        'JOB_REFRESH_FT_RPT_CURR',
        'JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR',
        'REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB',
        'JOB_REFRESH_D1_MSRMT_RPT_CURR',
        'JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR',
        'JOB_REFRESH_D1_USAGE_RPT_CURR',
        'JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR',
        'JOB_REFRESH_CMS_SA_SNAPSHOT'
      )
ORDER BY next_run_date, job_name;
