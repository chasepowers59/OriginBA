-- PERIODIC_REPORT: S5 semi_annual_finance_arrears_movement
-- FREQUENCY: semi_annual
-- WORKSTREAM: finance
-- GRAIN: SA_TYPE_CD
-- WINDOW: previous six full calendar months (arrears FT by accounting date)
-- SOURCE: FT_RPT_CURR (governed arrears pattern)

SELECT ft.sa_type_cd,
       ft.sa_type_desc,
       COUNT(*) AS arrears_ft_count,
       SUM(ft.cur_amt) AS total_arrears_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND ft.accounting_dt < TRUNC(SYSDATE, 'MM')
  AND ft.freeze_dttm IS NOT NULL
  AND NULLIF(TRIM(ft.sa_status_flg), '') = '20'
  AND NULLIF(TRIM(ft.ft_type_flg), '') NOT IN ('PS', 'PX')
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY ft.sa_type_cd, ft.sa_type_desc
HAVING SUM(ft.cur_amt) > 0
ORDER BY SUM(ft.cur_amt) DESC;
