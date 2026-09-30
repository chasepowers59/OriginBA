-- The write-off process behind each final notice. CI_WO_PROC carries no arrears or as-of date: the
-- amount is the sum over its service agreements and the as-of date is the process creation.
select cc_id, process_id, template_code, arrears_amount, arrears_as_of from (
  select c.cc_id, p.wo_proc_id as process_id, trim(p.wo_proc_tmpl_cd) as template_code,
         (select coalesce(sum(s.ars_amt), 0) from CISADM.ci_wo_proc_sa s where s.wo_proc_id = p.wo_proc_id) as arrears_amount,
         p.cre_dttm as arrears_as_of,
         row_number() over (partition by c.cc_id order by
           case when exists (select 1 from CISADM.ci_wo_evt e where e.wo_proc_id = p.wo_proc_id
                             and e.completion_dt >= trunc(c.cc_dttm) and e.completion_dt < trunc(c.cc_dttm) + 1) then 0 else 1 end,
           p.cre_dttm desc) as rn
  from CISADM.ci_cc c
  join CISADM.ci_wo_proc p on p.acct_id = c.acct_id and p.cre_dttm < trunc(c.cc_dttm) + 1
  where trim(c.print_letter_sw) = 'Y' and {filter}
) z where rn = 1
