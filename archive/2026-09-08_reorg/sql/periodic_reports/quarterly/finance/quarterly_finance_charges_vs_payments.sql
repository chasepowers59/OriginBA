-- PERIODIC_REPORT: Q3 quarterly_finance_charges_vs_payments
-- FREQUENCY: quarterly
-- WORKSTREAM: finance
-- GRAIN: FT category (charges / payments / adjustments)
-- WINDOW: previous full calendar quarter
-- SOURCE: FT_RPT_CURR

SELECT CASE
         WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('PS', 'PX') THEN 'PAYMENTS'
         WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX') THEN 'ADJUSTMENTS'
         ELSE 'CHARGES_AND_OTHER'
       END AS ft_category,
       COUNT(*) AS ft_count,
       SUM(ft.cur_amt) AS total_cur_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND ft.accounting_dt < TRUNC(SYSDATE, 'Q')
  AND ft.freeze_dttm IS NOT NULL
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY CASE
           WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('PS', 'PX') THEN 'PAYMENTS'
           WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX') THEN 'ADJUSTMENTS'
           ELSE 'CHARGES_AND_OTHER'
         END
ORDER BY ft_category;
