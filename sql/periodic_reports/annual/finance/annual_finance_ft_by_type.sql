-- PERIODIC_REPORT: A3 annual_finance_ft_by_type
-- FREQUENCY: annual
-- WORKSTREAM: finance
-- GRAIN: FT_TYPE_FLG + SA_TYPE_CD
-- WINDOW: previous full calendar year
-- SOURCE: FT_RPT_CURR
-- GOVERNED: frozen FT (freeze_dttm populated), active SA, exclude ODEV

SELECT ft.ft_type_flg,
       ft.ft_type_flg_desc,
       ft.sa_type_cd,
       ft.sa_type_desc,
       COUNT(*) AS ft_count,
       SUM(ft.cur_amt) AS total_cur_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'YYYY')
  AND ft.freeze_dttm IS NOT NULL
  AND NULLIF(TRIM(ft.sa_status_flg), '') = '20'
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY ft.ft_type_flg, ft.ft_type_flg_desc,
         ft.sa_type_cd, ft.sa_type_desc
ORDER BY ft.ft_type_flg, ft.sa_type_cd;
