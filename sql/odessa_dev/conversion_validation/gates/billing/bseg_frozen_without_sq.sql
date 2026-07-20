-- FAIL gate: frozen/complete water bseg missing CI_BSEG_SQ (blocks billed usage SQ reports).

PROMPT === Gate billing: frozen bseg without SQ (summary) ===

SELECT 'bseg_frozen_without_sq' AS check_id,
       'FAIL' AS severity,
       COUNT(*) AS failure_cnt
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
WHERE bs.bseg_stat_flg IN ('50', '40')
  AND sa.sa_type_cd LIKE 'W-%'
  AND bs.bseg_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (SELECT 1 FROM cisadm.ci_bseg_sq sq WHERE sq.bseg_id = bs.bseg_id)
HAVING COUNT(*) > 0;

PROMPT === Gate billing: frozen bseg without SQ (failure sample) ===

SELECT 'bseg_frozen_without_sq' AS check_id,
       'FAIL' AS severity,
       bs.bseg_id,
       bs.bill_id,
       bs.sa_id,
       bs.bseg_stat_flg,
       sa.sa_type_cd
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
WHERE bs.bseg_stat_flg IN ('50', '40')
  AND sa.sa_type_cd LIKE 'W-%'
  AND bs.bseg_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (SELECT 1 FROM cisadm.ci_bseg_sq sq WHERE sq.bseg_id = bs.bseg_id)
ORDER BY bs.bseg_id
FETCH FIRST 25 ROWS ONLY;
