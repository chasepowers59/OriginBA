-- FAIL gate: D1FA field activities missing service point linkage.

PROMPT === Gate field_ops: field activity without SP link (failure sample) ===

SELECT 'field_activity_no_sp' AS check_id,
       'FAIL' AS severity,
       a.d1_activity_id,
       a.activity_type_cd,
       a.bo_status_cd,
       a.start_dttm
FROM cisadm.d1_activity a
JOIN cisadm.d1_activity_type t
  ON t.activity_type_cd = a.activity_type_cd
 AND t.activity_type_cat_flg = 'D1FA'
WHERE a.d1_activity_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (
        SELECT 1
          FROM cisadm.d1_activity_rel_obj ro
         WHERE ro.d1_activity_id = a.d1_activity_id
           AND ro.maint_obj_cd = 'D1-SP'
      )
ORDER BY a.start_dttm DESC NULLS LAST
FETCH FIRST 100 ROWS ONLY;
