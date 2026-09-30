-- PERIODIC_REPORT: A8 annual_executive_scorecard
-- FREQUENCY: annual
-- WORKSTREAM: executive
-- GRAIN: one row per KPI
-- WINDOW: previous full calendar year
-- SOURCE: union of periodic report KPIs

SELECT 'billing_total_bill_sq' AS kpi_name,
       'billing' AS workstream,
       TO_CHAR(SUM(sq.total_bill_sq)) AS kpi_value
FROM cisadm.bseg_sq_usage_rpt_curr sq
WHERE sq.bill_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND sq.bill_dt < TRUNC(SYSDATE, 'YYYY')
  AND NULLIF(TRIM(sq.bseg_stat_flg), '') = '50'
  AND sq.acct_id NOT LIKE 'ODEV%'

UNION ALL

SELECT 'billing_total_billed_amt',
       'billing',
       TO_CHAR(SUM(bu.total_calc_amt))
FROM cisadm.bseg_billed_usage_rpt_curr bu
WHERE bu.bill_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND bu.bill_dt < TRUNC(SYSDATE, 'YYYY')
  AND NULLIF(TRIM(bu.bseg_stat_flg), '') = '50'
  AND bu.acct_id NOT LIKE 'ODEV%'

UNION ALL

SELECT 'finance_ft_total_cur_amt',
       'finance',
       TO_CHAR(SUM(ft.cur_amt))
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'YYYY')
  AND ft.freeze_dttm IS NOT NULL
  AND ft.acct_id NOT LIKE 'ODEV%'

UNION ALL

SELECT 'finance_adjustment_total_amt',
       'finance',
       TO_CHAR(SUM(ft.cur_amt))
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'YYYY')
  AND ft.freeze_dttm IS NOT NULL
  AND NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX')
  AND ft.acct_id NOT LIKE 'ODEV%'

UNION ALL

SELECT 'payments_total_tender_amt',
       'payments',
       TO_CHAR(SUM(pt.tender_amt))
FROM cisadm.pay_tndr_cash_rpt_curr pt
WHERE pt.pay_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND pt.pay_dt < TRUNC(SYSDATE, 'YYYY')
  AND pt.payor_acct_id NOT LIKE 'ODEV%'

UNION ALL

SELECT 'workflow_todo_items_created',
       'workflow',
       TO_CHAR(COUNT(*))
FROM cisadm.workflow_queue_rpt_curr wq
WHERE wq.queue_source = 'TODO'
  AND wq.td_cre_dttm >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND wq.td_cre_dttm < TRUNC(SYSDATE, 'YYYY')
  AND (wq.td_entry_id IS NULL OR wq.td_entry_id NOT LIKE 'ODEV%')

ORDER BY workstream, kpi_name;
