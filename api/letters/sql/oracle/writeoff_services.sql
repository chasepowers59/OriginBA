select s.wo_proc_id as process_id, s.sa_id, coalesce(t.descr, trim(sa.sa_type_cd)) as service_type, s.ars_amt as amount,
       coalesce(pr.address1, ' ') as address1, coalesce(pr.city, ' ') as city,
       coalesce(pr.state, ' ') as state, coalesce(pr.postal, ' ') as postal
from CISADM.ci_wo_proc_sa s
join CISADM.ci_sa sa on sa.sa_id = s.sa_id
left join CISADM.ci_sa_type_l t on trim(t.sa_type_cd) = trim(sa.sa_type_cd) and trim(t.cis_division) = trim(sa.cis_division) and trim(t.language_cd) = 'ENG'
left join CISADM.ci_prem pr on pr.prem_id = sa.char_prem_id
where s.wo_proc_id in (
  select p.wo_proc_id from CISADM.ci_wo_proc p join CISADM.ci_cc c on c.acct_id = p.acct_id
  where trim(c.print_letter_sw) = 'Y' and {filter})
order by s.wo_proc_id, s.sa_id
