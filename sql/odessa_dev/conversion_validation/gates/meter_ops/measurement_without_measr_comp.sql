-- WARN gate: processed measurements without measuring component link.

PROMPT === Gate meter_ops: msrmt without measr_comp (WARN sample) ===

SELECT 'msrmt_missing_measr_comp' AS check_id,
       'WARN' AS severity,
       m.measr_comp_id,
       m.msrmt_dttm,
       m.bo_status_cd
FROM cisadm.d1_msrmt m
WHERE m.measr_comp_id IS NOT NULL
  AND NOT EXISTS (
        SELECT 1 FROM cisadm.d1_measr_comp mc
         WHERE mc.measr_comp_id = m.measr_comp_id
      )
ORDER BY m.msrmt_dttm DESC NULLS LAST
FETCH FIRST 50 ROWS ONLY;
