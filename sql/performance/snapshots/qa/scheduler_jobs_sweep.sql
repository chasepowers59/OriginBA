-- Read-only: which snapshot refresh jobs exist and are enabled in THIS database.
-- The repo archived the ACCT_DEBT, COLL_PROC and PAY_TNDR_CASH scripts on 2026-09-08;
-- archiving a script does not stop a job. Run per client (VPN) and record the answer in
-- docs/governed_snapshot_delivery_status.md. If a retired job is enabled, decide with the
-- owner, then run scheduler_jobs_disable_retired.sql -- never as part of a sweep.
select owner, job_name, enabled, state, repeat_interval, last_start_date, next_run_date
from   all_scheduler_jobs
where  owner = 'CISADM'
and    (job_name like 'JOB_REFRESH_%'
     or job_name like 'JOB_BASELINE_%'
     or job_name like 'REFRESH_%'
     or job_name like 'JOB_ONCE_%')
order by case when job_name in ('JOB_REFRESH_ACCT_DEBT_RPT_CURR', 'JOB_REFRESH_COLL_PROC_RPT_CURR',
                                'REFRESH_PAY_TNDR_CASH_RPT_CURR_JB') then 0 else 1 end,
         job_name;
