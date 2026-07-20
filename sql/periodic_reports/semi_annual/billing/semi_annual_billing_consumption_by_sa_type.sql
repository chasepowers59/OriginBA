-- PERIODIC_REPORT: S1 semi_annual_billing_consumption_by_sa_type
-- FREQUENCY: semi_annual
-- WORKSTREAM: billing
-- GRAIN: SA_TYPE_CD + UOM_CD
-- WINDOW: previous six full calendar months
-- SOURCE: BSEG_SQ_USAGE_RPT_CURR

SELECT sq.sa_type_cd,
       sq.sa_type_desc,
       sq.uom_cd,
       sq.uom_desc,
       COUNT(DISTINCT sq.bseg_id) AS bseg_count,
       SUM(sq.total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_sq_usage_rpt_curr sq
WHERE sq.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND sq.bill_dt < TRUNC(SYSDATE, 'MM')
  AND NULLIF(TRIM(sq.bseg_stat_flg), '') = '50'
  AND sq.acct_id NOT LIKE 'ODEV%'
  AND sq.bseg_id NOT LIKE 'ODEV%'
GROUP BY sq.sa_type_cd, sq.sa_type_desc,
         sq.uom_cd, sq.uom_desc
ORDER BY sq.sa_type_cd, sq.uom_cd;
