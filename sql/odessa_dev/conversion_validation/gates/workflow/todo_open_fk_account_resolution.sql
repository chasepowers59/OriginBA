-- WARN gate: open/working todos that cannot resolve ACCT_ID via FK pivot.

PROMPT === Gate workflow: open todo without account FK (WARN sample) ===

SELECT 'todo_open_no_acct_fk' AS check_id,
       'WARN' AS severity,
       t.td_entry_id,
       t.td_type_cd,
       t.entry_status_flg,
       t.assigned_to
FROM cisadm.ci_td_entry t
WHERE t.entry_status_flg IN ('O', 'W')
  AND t.td_entry_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (
        SELECT 1
          FROM cisadm.ci_td_drlkey k
          JOIN cisadm.ci_td_drlkey_ty ty
            ON ty.td_type_cd = t.td_type_cd
           AND ty.seq_num = k.seq_num
         WHERE k.td_entry_id = t.td_entry_id
           AND ty.tbl_name = 'CI_ACCT'
      )
ORDER BY t.cre_dttm DESC NULLS LAST
FETCH FIRST 25 ROWS ONLY;
