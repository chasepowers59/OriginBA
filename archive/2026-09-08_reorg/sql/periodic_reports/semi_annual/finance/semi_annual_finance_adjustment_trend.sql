-- PERIODIC_REPORT: S4 semi_annual_finance_adjustment_trend
-- FREQUENCY: semi_annual
-- WORKSTREAM: finance
-- GRAIN: accounting month + ADJ_TYPE_CD
-- WINDOW: previous six full calendar months
-- SOURCE: FT_RPT_CURR

SELECT TRUNC(ft.accounting_dt, 'MM') AS accounting_month,
       ft.adj_type_cd,
       ft.adj_type_desc,
       COUNT(*) AS adj_ft_count,
       SUM(ft.cur_amt) AS total_adj_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND ft.accounting_dt < TRUNC(SYSDATE, 'MM')
  AND ft.freeze_dttm IS NOT NULL
  AND NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX')
  AND ft.adj_type_cd IS NOT NULL
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY TRUNC(ft.accounting_dt, 'MM'),
         ft.adj_type_cd, ft.adj_type_desc
ORDER BY accounting_month, ft.adj_type_cd;
