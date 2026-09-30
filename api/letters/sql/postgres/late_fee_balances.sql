-- The account balance as of each late fee's own date, keyed by the adjustment.
select a.adj_id, coalesce(sum(f.cur_amt), 0) as balance
from ci_adj a
join ci_sa fee_sa on fee_sa.sa_id = a.sa_id
join ci_sa sa on sa.acct_id = fee_sa.acct_id
join ci_ft f on f.sa_id = sa.sa_id and trim(f.freeze_sw) = 'Y' and f.freeze_dttm < a.cre_dt::date + 1
where trim(a.adj_type_cd) in ({types}) and trim(a.adj_status_flg) = '50' and {filter}
group by a.adj_id
