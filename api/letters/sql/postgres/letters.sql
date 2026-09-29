-- Printable customer contacts (Print Letter = Y) with the recipient's two candidate address
-- blocks: the person's own address and the account's mailing premise. CI_ACCT_PER.BILL_ADDR_SRCE_FLG
-- says which one C2M would use (PER = person, PREM = mailing premise on account; the account
-- override rows are not landed, so ACOV falls back to the premise); the repository picks.
-- The recipient name is the person's override mail name when set, else the primary name.
-- {filter} is either the contact date window or one CC_ID.
select c.cc_id, c.cc_dttm, trim(c.cc_cl_cd) as contact_class, trim(c.cc_type_cd) as contact_type,
       coalesce(tl.descr, '') as contact_type_description, trim(coalesce(c.ltr_tmpl_cd, '')) as template_code,
       coalesce(c.descrlong, '') as body, c.letter_print_dttm,
       c.acct_id as account_id, c.per_id as person_id, coalesce(pn.entity_name, '') as customer_name,
       trim(coalesce(ap.bill_addr_srce_flg, '')) as address_source, coalesce(ap.nbr_bill_copies, 1)::int as copies,
       coalesce(nullif(trim(p.ovrd_mail_name1), ''), pn.entity_name, '') as name1, coalesce(p.ovrd_mail_name2, '') as name2, coalesce(p.ovrd_mail_name3, '') as name3,
       p.address1 as p_address1, p.address2 as p_address2, p.address3 as p_address3, p.address4 as p_address4, p.city as p_city, p.state as p_state, p.postal as p_postal, p.country as p_country,
       pr.address1 as m_address1, pr.address2 as m_address2, pr.address3 as m_address3, pr.address4 as m_address4, pr.city as m_city, pr.state as m_state, pr.postal as m_postal, pr.country as m_country
from ci_cc c
left join ci_cc_type_l tl on trim(tl.cc_cl_cd) = trim(c.cc_cl_cd) and trim(tl.cc_type_cd) = trim(c.cc_type_cd) and trim(tl.language_cd) = 'ENG'
left join ci_acct a on a.acct_id = c.acct_id
left join ci_acct_per ap on ap.acct_id = c.acct_id and ap.per_id = c.per_id
left join ci_per p on p.per_id = c.per_id
left join ci_per_name pn on pn.per_id = c.per_id and trim(pn.prim_name_sw) = 'Y'
left join ci_prem pr on pr.prem_id = coalesce(a.mailing_prem_id, c.prem_id)
where trim(c.print_letter_sw) = 'Y' and {filter}
order by c.cc_dttm, c.cc_id
