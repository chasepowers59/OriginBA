-- PERIODIC_REPORT: A2 annual_billing_revenue_by_customer_class
-- FREQUENCY: annual
-- WORKSTREAM: billing
-- GRAIN: CUST_CL_CD + SA_TYPE_CD
-- WINDOW: previous full calendar year
-- SOURCE: BSEG_BILLED_USAGE_RPT_CURR
-- GOVERNED: frozen segments, exclude ODEV test rows

SELECT bu.cust_cl_cd,
       bu.cust_cl_desc,
       bu.sa_type_cd,
       bu.sa_type_desc,
       COUNT(DISTINCT bu.bseg_id) AS bseg_count,
       SUM(bu.total_calc_amt) AS total_billed_amt,
       SUM(bu.total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_billed_usage_rpt_curr bu
WHERE bu.bill_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND bu.bill_dt < TRUNC(SYSDATE, 'YYYY')
  AND NULLIF(TRIM(bu.bseg_stat_flg), '') = '50'
  AND bu.acct_id NOT LIKE 'ODEV%'
  AND bu.bseg_id NOT LIKE 'ODEV%'
GROUP BY bu.cust_cl_cd, bu.cust_cl_desc,
         bu.sa_type_cd, bu.sa_type_desc
ORDER BY bu.cust_cl_cd, bu.sa_type_cd;
