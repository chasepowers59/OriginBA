-- Frozen late payment charge adjustments (types from config/letters.yml, status 50 = Frozen), each
-- with the account's main customer and mailing premise for the recipient block. {types} is one
-- bind per type, {filter} the created-date window or one ADJ_ID.
select a.adj_id, a.adj_amt as amount, a.cre_dt as charged_on, a.sa_id, sa.acct_id as account_id,
       coalesce(t.descr, trim(sa.sa_type_cd)) as service_type,
       coalesce(sp.address1, '') as sp_address1, coalesce(sp.city, '') as sp_city, coalesce(sp.state, '') as sp_state, coalesce(sp.postal, '') as sp_postal,
       ap.per_id as person_id, coalesce(pn.entity_name, '') as customer_name,
       trim(coalesce(ap.bill_addr_srce_flg, '')) as address_source, coalesce(ap.nbr_bill_copies, 1)::int as copies,
       coalesce(nullif(trim(p.ovrd_mail_name1), ''), pn.entity_name, '') as name1, coalesce(p.ovrd_mail_name2, '') as name2, coalesce(p.ovrd_mail_name3, '') as name3,
       p.address1 as p_address1, p.address2 as p_address2, p.address3 as p_address3, p.address4 as p_address4, p.city as p_city, p.state as p_state, p.postal as p_postal, p.country as p_country,
       pr.address1 as m_address1, pr.address2 as m_address2, pr.address3 as m_address3, pr.address4 as m_address4, pr.city as m_city, pr.state as m_state, pr.postal as m_postal, pr.country as m_country
from ci_adj a
join ci_sa sa on sa.sa_id = a.sa_id
left join ci_sa_type_l t on trim(t.sa_type_cd) = trim(sa.sa_type_cd) and trim(t.cis_division) = trim(sa.cis_division) and trim(t.language_cd) = 'ENG'
left join ci_prem sp on sp.prem_id = sa.char_prem_id
left join ci_acct ac on ac.acct_id = sa.acct_id
left join ci_acct_per ap on ap.acct_id = sa.acct_id and trim(ap.main_cust_sw) = 'Y'
left join ci_per p on p.per_id = ap.per_id
left join ci_per_name pn on pn.per_id = ap.per_id and trim(pn.prim_name_sw) = 'Y'
left join ci_prem pr on pr.prem_id = ac.mailing_prem_id
where trim(a.adj_type_cd) in ({types}) and trim(a.adj_status_flg) = '50' and {filter}
order by a.cre_dt, a.adj_id
