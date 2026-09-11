-- PERIODIC_REPORT: A6 annual_payments_by_tender
-- FREQUENCY: annual
-- WORKSTREAM: payments
-- GRAIN: TENDER_TYPE_CD + SOURCE_FAMILY_CD
-- WINDOW: previous full calendar year
-- SOURCE: PAY_TNDR_CASH_RPT_CURR
-- GOVERNED: exclude ODEV test accounts

SELECT pt.tender_type_cd,
       pt.tender_type_desc,
       pt.source_family_cd,
       pt.source_family_desc,
       COUNT(*) AS tender_count,
       SUM(pt.tender_amt) AS total_tender_amt
FROM cisadm.pay_tndr_cash_rpt_curr pt
WHERE pt.pay_dt >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND pt.pay_dt < TRUNC(SYSDATE, 'YYYY')
  AND pt.payor_acct_id NOT LIKE 'ODEV%'
GROUP BY pt.tender_type_cd, pt.tender_type_desc,
         pt.source_family_cd, pt.source_family_desc
ORDER BY SUM(pt.tender_amt) DESC;
