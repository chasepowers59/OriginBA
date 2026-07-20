-- WARN gate: high share of water SQ rows are DAYS+GAL+bill_sq=1 (Odessa-specific pattern).

PROMPT === Gate 06: water BSEG SQ DAYS/GAL pattern (WARN if >95%) ===

SELECT '06_water_sq_days_gal_one' AS check_id,
       'WARN' AS severity,
       'Water SQ rows with SQI=DAYS UOM=GAL bill_sq=1' AS detail,
       TO_CHAR(ROUND(100 * days_gal_one / NULLIF(sq_rows, 0), 1)) || '%' AS metric
FROM (
  SELECT COUNT(*) AS sq_rows,
         SUM(CASE
               WHEN sq.sqi_cd = 'DAYS' AND sq.uom_cd = 'GAL' AND sq.bill_sq = 1
               THEN 1 ELSE 0
             END) AS days_gal_one
  FROM cisadm.ci_bseg_sq sq
  JOIN cisadm.ci_bseg bs ON bs.bseg_id = sq.bseg_id
  JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
  WHERE sa.sa_type_cd LIKE 'W-%'
)
WHERE sq_rows > 0
  AND days_gal_one / sq_rows > 0.95;
