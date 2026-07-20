-- WARN gate: high share of D1_USAGE rows lack C1_USAGE bridge (BD-PROC).

PROMPT === Gate usage: D1_USAGE without C1 bridge (WARN if >20% sample) ===

SELECT 'usage_missing_c1_bridge' AS check_id,
       'WARN' AS severity,
       'D1_USAGE rows without matching C1_USAGE BD-PROC' AS detail,
       TO_CHAR(ROUND(100 * missing_cnt / NULLIF(total_cnt, 0), 1)) || '%' AS metric
FROM (
  SELECT COUNT(*) AS total_cnt,
         SUM(CASE WHEN c.usage_id IS NULL THEN 1 ELSE 0 END) AS missing_cnt
    FROM cisadm.d1_usage u
    LEFT JOIN cisadm.c1_usage c
           ON c.usage_id = u.usg_ext_id
          AND c.bo_status_cd = 'BD-PROC'
   WHERE u.d1_usage_id NOT LIKE 'ODEV%'
)
WHERE total_cnt > 100
  AND missing_cnt / total_cnt > 0.20;
