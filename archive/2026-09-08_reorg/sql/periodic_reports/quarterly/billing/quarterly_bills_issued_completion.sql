-- PERIODIC_REPORT: Q2 quarterly_bills_issued_completion
-- FREQUENCY: quarterly
-- WORKSTREAM: billing
-- GRAIN: BILL_STAT_FLG + BSEG completion
-- WINDOW: previous full calendar quarter
-- SOURCE: CI_BILL + CI_BSEG

SELECT NULLIF(TRIM(b.bill_stat_flg), '') AS bill_stat_flg,
       COUNT(DISTINCT b.bill_id) AS bill_count,
       COUNT(DISTINCT bs.bseg_id) AS bseg_count,
       SUM(CASE WHEN NULLIF(TRIM(bs.bseg_stat_flg), '') = '50' THEN 1 ELSE 0 END) AS frozen_bseg_count
FROM cisadm.ci_bill b
LEFT JOIN cisadm.ci_bseg bs ON bs.bill_id = b.bill_id
WHERE b.bill_dt >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND b.bill_dt < TRUNC(SYSDATE, 'Q')
  AND b.acct_id NOT LIKE 'ODEV%'
GROUP BY NULLIF(TRIM(b.bill_stat_flg), '')
ORDER BY bill_stat_flg;
