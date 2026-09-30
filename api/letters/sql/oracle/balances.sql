-- Keyed by the LETTER, never the account: the balance is as of each letter's own date, and two
-- letters to one account on different dates carry different balances. One query for every letter
-- the {filter} selects (measured on Ellensburg: 3.35s for 1,775 letters against 16.9s one at a time).
select c.cc_id, coalesce(sum(f.cur_amt), 0) as balance
from CISADM.ci_cc c
join CISADM.ci_sa sa on sa.acct_id = c.acct_id
join CISADM.ci_ft f on f.sa_id = sa.sa_id and trim(f.freeze_sw) = 'Y' and f.freeze_dttm < trunc(c.cc_dttm) + 1
where trim(c.print_letter_sw) = 'Y' and {filter}
group by c.cc_id
