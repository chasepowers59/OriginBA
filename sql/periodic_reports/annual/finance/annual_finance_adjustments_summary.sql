-- PERIODIC_REPORT: A5 annual_finance_adjustments_summary
-- FREQUENCY: annual
-- WORKSTREAM: finance
-- GRAIN: ADJ_TYPE_CD
-- WINDOW: previous full calendar year
-- SOURCE: FT_RPT_CURR (adjustment FT rows)
-- GOVERNED: frozen FT, exclude ODEV

SELECT ft.adj_type_cd,
       ft.adj_type_desc,
       COUNT(*) AS adj_ft_count,
       SUM(ft.cur_amt) AS total_adj_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'YYYY')
  AND ft.freeze_dttm IS NOT NULL
  AND NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX')
  AND ft.adj_type_cd IS NOT NULL
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY ft.adj_type_cd, ft.adj_type_desc
ORDER BY ABS(SUM(ft.cur_amt)) DESC;
