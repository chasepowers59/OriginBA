-- The collection process behind each letter: no key links CI_CC to CI_COLL_EVT, so it is the process
-- on the account with an event COMPLETED on the letter's date, else the newest created by then.
select cc_id, process_id, template_code, arrears_amount, arrears_as_of from (
  select c.cc_id, p.coll_proc_id as process_id, trim(p.coll_proc_tmpl_cd) as template_code,
         p.ars_amt as arrears_amount, p.coll_ars_dt as arrears_as_of,
         row_number() over (partition by c.cc_id order by
           case when exists (select 1 from CISADM.ci_coll_evt e where e.coll_proc_id = p.coll_proc_id
                             and e.completion_dt >= trunc(c.cc_dttm) and e.completion_dt < trunc(c.cc_dttm) + 1) then 0 else 1 end,
           p.cre_dttm desc) as rn
  from CISADM.ci_cc c
  join CISADM.ci_coll_proc p on p.acct_id = c.acct_id and p.cre_dttm < trunc(c.cc_dttm) + 1
  where trim(c.print_letter_sw) = 'Y' and {filter}
) z where rn = 1
