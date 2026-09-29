-- Base-product event statuses: 10 Pending, 20 Awaiting Field Activity, 30 Completed, 40 Canceled.
select e.wo_proc_id as process_id, e.evt_seq, trim(e.wo_evt_typ_cd) as event_type_cd,
       coalesce(l.descr, trim(e.wo_evt_typ_cd)) as event_type,
       trim(e.wo_evt_stat_flg) as status_cd, e.trigger_dt, e.completion_dt
from CISADM.ci_wo_evt e
left join CISADM.ci_wo_evt_typ_l l on trim(l.wo_evt_typ_cd) = trim(e.wo_evt_typ_cd) and trim(l.language_cd) = 'ENG'
where e.wo_proc_id in (
  select p.wo_proc_id from CISADM.ci_wo_proc p join CISADM.ci_cc c on c.acct_id = p.acct_id
  where trim(c.print_letter_sw) = 'Y' and {filter})
order by e.wo_proc_id, e.evt_seq
