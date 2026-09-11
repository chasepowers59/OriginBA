-- PERIODIC_REPORT: Q8 quarterly_billing_bseg_without_sq
-- FREQUENCY: quarterly
-- WORKSTREAM: billing
-- GRAIN: SA_TYPE_CD
-- WINDOW: previous full calendar quarter (frozen water bsegs)
-- SOURCE: CI_BSEG + CI_SA (conversion quality metric)

SELECT sa.sa_type_cd,
       COUNT(*) AS frozen_bseg_without_sq_count
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
WHERE bs.bseg_stat_flg IN ('50', '40')
  AND sa.sa_type_cd LIKE 'W-%'
  AND bs.bseg_id NOT LIKE 'ODEV%'
  AND bs.end_dt >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND bs.end_dt < TRUNC(SYSDATE, 'Q')
  AND NOT EXISTS (
        SELECT 1
          FROM cisadm.ci_bseg_sq sq
         WHERE sq.bseg_id = bs.bseg_id
      )
GROUP BY sa.sa_type_cd
ORDER BY COUNT(*) DESC;
