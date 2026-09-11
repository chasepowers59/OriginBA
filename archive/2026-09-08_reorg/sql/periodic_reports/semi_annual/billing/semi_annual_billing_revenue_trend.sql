-- PERIODIC_REPORT: S2 semi_annual_billing_revenue_trend
-- FREQUENCY: semi_annual
-- WORKSTREAM: billing
-- GRAIN: bill month (TRUNC BILL_DT)
-- WINDOW: previous six full calendar months
-- SOURCE: BSEG_BILLED_USAGE_RPT_CURR

SELECT TRUNC(bu.bill_dt, 'MM') AS bill_month,
       COUNT(DISTINCT bu.bseg_id) AS bseg_count,
       SUM(bu.total_calc_amt) AS total_billed_amt,
       SUM(bu.total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_billed_usage_rpt_curr bu
WHERE bu.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND bu.bill_dt < TRUNC(SYSDATE, 'MM')
  AND NULLIF(TRIM(bu.bseg_stat_flg), '') = '50'
  AND bu.acct_id NOT LIKE 'ODEV%'
GROUP BY TRUNC(bu.bill_dt, 'MM')
ORDER BY bill_month;
