-- Every CANDIDATE process for the letters' accounts rather than an id list (Oracle caps IN at 1,000).
-- Base-product event statuses: 10 Pending, 20 Awaiting Field Activity, 30 Completed, 40 Canceled.
select e.coll_proc_id as process_id, e.evt_seq, trim(e.coll_evt_typ_cd) as event_type_cd,
       coalesce(l.descr, trim(e.coll_evt_typ_cd)) as event_type,
       trim(e.coll_evt_stat_flg) as status_cd, e.trigger_dt, e.completion_dt
from ci_coll_evt e
left join ci_coll_evt_typ_l l on trim(l.coll_evt_typ_cd) = trim(e.coll_evt_typ_cd) and trim(l.language_cd) = 'ENG'
where e.coll_proc_id in (
  select p.coll_proc_id from ci_coll_proc p join ci_cc c on c.acct_id = p.acct_id
  where trim(c.print_letter_sw) = 'Y' and {filter})
order by e.coll_proc_id, e.evt_seq
