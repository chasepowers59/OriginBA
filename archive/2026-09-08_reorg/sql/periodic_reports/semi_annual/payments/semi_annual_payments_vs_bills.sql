-- PERIODIC_REPORT: S3 semi_annual_payments_vs_bills
-- FREQUENCY: semi_annual
-- WORKSTREAM: payments
-- GRAIN: FT category rollup
-- WINDOW: previous six full calendar months
-- SOURCE: FT_RPT_CURR

SELECT CASE
         WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('PS', 'PX') THEN 'PAYMENTS'
         WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('BS', 'BX') THEN 'BILL_SEGMENTS'
         WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX') THEN 'ADJUSTMENTS'
         ELSE 'OTHER'
       END AS ft_category,
       COUNT(*) AS ft_count,
       SUM(ft.cur_amt) AS total_cur_amt
FROM cisadm.ft_rpt_curr ft
WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND ft.accounting_dt < TRUNC(SYSDATE, 'MM')
  AND ft.freeze_dttm IS NOT NULL
  AND ft.acct_id NOT LIKE 'ODEV%'
GROUP BY CASE
           WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('PS', 'PX') THEN 'PAYMENTS'
           WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('BS', 'BX') THEN 'BILL_SEGMENTS'
           WHEN NULLIF(TRIM(ft.ft_type_flg), '') IN ('AD', 'AX') THEN 'ADJUSTMENTS'
           ELSE 'OTHER'
         END
ORDER BY ft_category;
