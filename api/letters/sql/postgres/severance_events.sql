-- Base-product event statuses: 10 Pending, 20 Awaiting Field Activity, 30 Completed, 40 Canceled.
select e.sev_proc_id as process_id, e.evt_seq, trim(e.sev_evt_type_cd) as event_type_cd,
       coalesce(l.descr, trim(e.sev_evt_type_cd)) as event_type,
       trim(e.sev_evt_stat_flg) as status_cd, e.trigger_dt, e.completion_dt
from ci_sev_evt e
left join ci_sev_evt_type_l l on trim(l.sev_evt_type_cd) = trim(e.sev_evt_type_cd) and trim(l.language_cd) = 'ENG'
where e.sev_proc_id in (
  select p.sev_proc_id from ci_sev_proc p join ci_sa sa on sa.sa_id = p.sa_id join ci_cc c on c.acct_id = sa.acct_id
  where trim(c.print_letter_sw) = 'Y' and {filter})
order by e.sev_proc_id, e.evt_seq
