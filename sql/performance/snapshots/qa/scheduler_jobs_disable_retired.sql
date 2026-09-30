-- DISABLES three scheduler jobs. Not read-only. Run only after scheduler_jobs_sweep.sql
-- showed them enabled and the owner chose to stop them; each statement is independent so
-- a job that does not exist (ORA-27476) does not block the others.
begin dbms_scheduler.disable('CISADM.JOB_REFRESH_ACCT_DEBT_RPT_CURR', force => true); exception when others then dbms_output.put_line('ACCT_DEBT: ' || sqlerrm); end;
/
begin dbms_scheduler.disable('CISADM.JOB_REFRESH_COLL_PROC_RPT_CURR', force => true); exception when others then dbms_output.put_line('COLL_PROC: ' || sqlerrm); end;
/
begin dbms_scheduler.disable('CISADM.REFRESH_PAY_TNDR_CASH_RPT_CURR_JB', force => true); exception when others then dbms_output.put_line('PAY_TNDR_CASH: ' || sqlerrm); end;
/
