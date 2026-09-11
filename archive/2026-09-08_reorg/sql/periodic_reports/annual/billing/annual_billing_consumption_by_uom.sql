-- PERIODIC_REPORT: A1 annual_billing_consumption_by_uom
-- FREQUENCY: annual
-- WORKSTREAM: billing
-- GRAIN: SA_TYPE_CD + UOM_CD + SQI_CD
-- WINDOW: previous full calendar year
-- SOURCE: BSEG_SQ_USAGE_RPT_CURR
-- GOVERNED: completed bill segments, exclude ODEV test rows

SELECT sq.sa_type_cd,
       sq.sa_type_desc,
       sq.uom_cd,
       sq.uom_desc,
       sq.sqi_cd,
       sq.sqi_desc,
       COUNT(DISTINCT sq.bseg_id) AS bseg_count,
       SUM(sq.total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_sq_usage_rpt_curr sq
WHERE sq.bill_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND sq.bill_dt < TRUNC(SYSDATE, 'YYYY')
  AND NULLIF(TRIM(sq.bseg_stat_flg), '') = '50'
  AND sq.acct_id NOT LIKE 'ODEV%'
  AND sq.bseg_id NOT LIKE 'ODEV%'
GROUP BY sq.sa_type_cd, sq.sa_type_desc,
         sq.uom_cd, sq.uom_desc,
         sq.sqi_cd, sq.sqi_desc
ORDER BY sq.sa_type_cd, sq.uom_cd, sq.sqi_cd;
