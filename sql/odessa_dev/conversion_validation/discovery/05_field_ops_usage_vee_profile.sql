-- Discovery: field ops + VEE + usage profile (informational).

PROMPT === Field ops: D1FA activity counts ===

SELECT COUNT(*) AS d1fa_activity_cnt
FROM cisadm.d1_activity a
JOIN cisadm.d1_activity_type t
  ON t.activity_type_cd = a.activity_type_cd
 AND t.activity_type_cat_flg = 'D1FA';

PROMPT === VEE: exception counts by status ===

SELECT bo_status_cd, COUNT(*) AS cnt
FROM cisadm.d1_vee_excp
GROUP BY bo_status_cd
ORDER BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT === Usage: D1 vs C1 bridge ===

SELECT COUNT(*) AS d1_usage_cnt,
       SUM(CASE WHEN c.usage_id IS NOT NULL THEN 1 ELSE 0 END) AS with_c1_bd_proc
FROM cisadm.d1_usage u
LEFT JOIN cisadm.c1_usage c
       ON c.usage_id = u.usg_ext_id
      AND c.bo_status_cd = 'BD-PROC';

PROMPT === Usage: measurement counts ===

SELECT COUNT(*) AS d1_msrmt_cnt FROM cisadm.d1_msrmt;
