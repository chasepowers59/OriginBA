-- The NSF letter's payment: the contact's characteristic points at the fee adjustment
-- (CI_CC_CHAR.CHAR_VAL_FK1 = CI_ADJ.ADJ_ID) and the cancelled tender points back at it
-- (CI_PAY_TNDR.ADJ_ID). MICR_ID is never selected: the reporting-scope fence refuses it.
select cc_id, adjustment_id, fee_amount, payment_date, payment_amount, tender_type from (
  select ch.cc_id, a.adj_id as adjustment_id, a.adj_amt as fee_amount, pe.pay_dt as payment_date,
         t.tender_amt as payment_amount, coalesce(tt.descr, trim(t.tender_type_cd), ' ') as tender_type,
         row_number() over (partition by ch.cc_id order by a.cre_dt desc) as rn
  from CISADM.ci_cc c
  join CISADM.ci_cc_char ch on ch.cc_id = c.cc_id
  join CISADM.ci_adj a on a.adj_id = ch.char_val_fk1
  left join CISADM.ci_pay_tndr t on t.adj_id = a.adj_id
  left join CISADM.ci_pay_event pe on pe.pay_event_id = t.pay_event_id
  left join CISADM.ci_tender_type_l tt on trim(tt.tender_type_cd) = trim(t.tender_type_cd) and trim(tt.language_cd) = 'ENG'
  where trim(c.print_letter_sw) = 'Y' and {filter}
) z where rn = 1
