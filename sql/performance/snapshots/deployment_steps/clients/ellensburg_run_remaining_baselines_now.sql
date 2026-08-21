-- Kick remaining Ellensburg one-time baseline jobs immediately (no stagger).
-- Leaves already-SUCCEEDED jobs alone.

BEGIN
  FOR r IN (
    SELECT job_name
    FROM all_scheduler_jobs
    WHERE owner = 'CISADM'
      AND job_name IN (
        'JOB_BASELINE_BSEG_SQ_USAGE_RPT_CURR_ONCE',
        'JOB_BASELINE_D1_MSRMT_RPT_CURR_ONCE',
        'JOB_BASELINE_FT_GL_DISTRIBUTION_RPT_CURR_ONCE',
        'JOB_BASELINE_D1_USAGE_RPT_CURR_ONCE',
        'JOB_BASELINE_D1_USAGE_SCALAR_DTL_RPT_CURR_ONCE'
      )
      AND state IN ('SCHEDULED', 'DISABLED')
  ) LOOP
    BEGIN
      DBMS_SCHEDULER.ENABLE(name => 'CISADM.' || r.job_name);
    EXCEPTION
      WHEN OTHERS THEN
        NULL;
    END;
    DBMS_SCHEDULER.RUN_JOB(
      job_name            => 'CISADM.' || r.job_name,
      use_current_session => FALSE
    );
  END LOOP;
END;
/
