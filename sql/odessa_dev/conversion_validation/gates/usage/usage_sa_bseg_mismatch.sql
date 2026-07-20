-- FAIL gate: C1_USAGE BD-PROC linked to bseg but SA mismatch.

PROMPT === Gate usage: C1_USAGE SA mismatch vs BSEG (failure sample) ===

SELECT 'usage_sa_bseg_mismatch' AS check_id,
       'FAIL' AS severity,
       c.usage_id,
       c.bseg_id,
       c.sa_id AS c1_sa_id,
       bs.sa_id AS bseg_sa_id
FROM cisadm.c1_usage c
JOIN cisadm.ci_bseg bs ON bs.bseg_id = c.bseg_id
WHERE c.bo_status_cd = 'BD-PROC'
  AND c.bseg_id IS NOT NULL
  AND c.sa_id <> bs.sa_id
  AND c.usage_id NOT LIKE 'ODEV%'
ORDER BY c.usage_id
FETCH FIRST 100 ROWS ONLY;
