-- WARN gate: VEE exceptions without IMD → measuring component chain.

PROMPT === Gate vee: exception without IMD/measr_comp (WARN sample) ===

SELECT 'vee_missing_imd_chain' AS check_id,
       'WARN' AS severity,
       v.vee_excp_id,
       v.init_msrmt_data_id,
       v.bo_status_cd,
       v.cre_dttm
FROM cisadm.d1_vee_excp v
WHERE v.vee_excp_id NOT LIKE 'ODEV%'
  AND (
        v.init_msrmt_data_id IS NULL
     OR NOT EXISTS (
          SELECT 1
            FROM cisadm.d1_init_msrmt_data imd
            JOIN cisadm.d1_measr_comp mc ON mc.measr_comp_id = imd.measr_comp_id
           WHERE imd.init_msrmt_data_id = v.init_msrmt_data_id
        )
      )
ORDER BY v.cre_dttm DESC NULLS LAST
FETCH FIRST 100 ROWS ONLY;
