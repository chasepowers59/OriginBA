-- FAIL gate: field activity cannot reach CI_PREM via D1EI bridge (same pattern as devices).

PROMPT === Gate field_ops: activity SP without premise bridge (summary) ===

SELECT 'field_activity_no_premise' AS check_id,
       'FAIL' AS severity,
       COUNT(*) AS failure_cnt
FROM cisadm.d1_activity a
JOIN cisadm.d1_activity_type t
  ON t.activity_type_cd = a.activity_type_cd
 AND t.activity_type_cat_flg = 'D1FA'
JOIN cisadm.d1_activity_rel_obj ro
  ON ro.d1_activity_id = a.d1_activity_id
 AND ro.maint_obj_cd = 'D1-SP'
LEFT JOIN cisadm.d1_sp_identifier spid
       ON spid.d1_sp_id = ro.pk_value1
      AND spid.sp_id_type_flg = 'D1EI'
LEFT JOIN cisadm.ci_sp sp ON sp.sp_id = spid.id_value
LEFT JOIN cisadm.ci_prem prem ON prem.prem_id = sp.prem_id
WHERE a.d1_activity_id NOT LIKE 'ODEV%'
  AND prem.prem_id IS NULL
HAVING COUNT(*) > 0;

PROMPT === Gate field_ops: activity SP without premise bridge (failure sample) ===

SELECT 'field_activity_no_premise' AS check_id,
       'FAIL' AS severity,
       a.d1_activity_id,
       ro.pk_value1 AS d1_sp_id,
       spid.id_value AS ci_sp_id,
       prem.address1
FROM cisadm.d1_activity a
JOIN cisadm.d1_activity_type t
  ON t.activity_type_cd = a.activity_type_cd
 AND t.activity_type_cat_flg = 'D1FA'
JOIN cisadm.d1_activity_rel_obj ro
  ON ro.d1_activity_id = a.d1_activity_id
 AND ro.maint_obj_cd = 'D1-SP'
LEFT JOIN cisadm.d1_sp_identifier spid
       ON spid.d1_sp_id = ro.pk_value1
      AND spid.sp_id_type_flg = 'D1EI'
LEFT JOIN cisadm.ci_sp sp ON sp.sp_id = spid.id_value
LEFT JOIN cisadm.ci_prem prem ON prem.prem_id = sp.prem_id
WHERE a.d1_activity_id NOT LIKE 'ODEV%'
  AND prem.prem_id IS NULL
ORDER BY a.d1_activity_id
FETCH FIRST 25 ROWS ONLY;
