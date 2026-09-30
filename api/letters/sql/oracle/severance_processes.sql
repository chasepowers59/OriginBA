-- The severance process behind each disconnection letter: one per service agreement, reached through
-- the account's SAs, chosen by the same completed-on-the-letter-date rule.
select cc_id, process_id, template_code, arrears_amount, arrears_as_of, sa_id, service_type, address1, city, state, postal from (
  select c.cc_id, p.sev_proc_id as process_id, trim(p.sev_proc_tmpl_cd) as template_code,
         p.ars_amt as arrears_amount, p.sev_ars_dt as arrears_as_of, p.sa_id,
         coalesce(t.descr, trim(sa.sa_type_cd)) as service_type,
         coalesce(pr.address1, ' ') as address1, coalesce(pr.city, ' ') as city,
         coalesce(pr.state, ' ') as state, coalesce(pr.postal, ' ') as postal,
         row_number() over (partition by c.cc_id order by
           case when exists (select 1 from CISADM.ci_sev_evt e where e.sev_proc_id = p.sev_proc_id
                             and e.completion_dt >= trunc(c.cc_dttm) and e.completion_dt < trunc(c.cc_dttm) + 1) then 0 else 1 end,
           p.cre_dttm desc) as rn
  from CISADM.ci_cc c
  join CISADM.ci_sa sa on sa.acct_id = c.acct_id
  join CISADM.ci_sev_proc p on p.sa_id = sa.sa_id and p.cre_dttm < trunc(c.cc_dttm) + 1
  left join CISADM.ci_sa_type_l t on trim(t.sa_type_cd) = trim(sa.sa_type_cd) and trim(t.cis_division) = trim(sa.cis_division) and trim(t.language_cd) = 'ENG'
  left join CISADM.ci_prem pr on pr.prem_id = sa.char_prem_id
  where trim(c.print_letter_sw) = 'Y' and {filter}
) z where rn = 1
