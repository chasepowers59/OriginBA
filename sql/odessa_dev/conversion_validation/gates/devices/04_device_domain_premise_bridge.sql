-- FAIL gate: install event cannot reach CI_PREM via D1EI -> CI_SP (domain report chain).

PROMPT === Gate 04: device-to-premise bridge (failure rows only) ===

SELECT '04_no_premise_bridge' AS check_id,
       'FAIL' AS severity,
       ie.install_evt_id,
       ie.d1_sp_id,
       spid.id_value AS ci_sp_id,
       prem.prem_id,
       prem.address1
FROM cisadm.d1_install_evt ie
LEFT JOIN cisadm.d1_sp_identifier spid
       ON spid.d1_sp_id = ie.d1_sp_id
      AND spid.sp_id_type_flg = 'D1EI'
LEFT JOIN cisadm.ci_sp sp
       ON sp.sp_id = spid.id_value
LEFT JOIN cisadm.ci_prem prem
       ON prem.prem_id = sp.prem_id
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND ie.bo_status_cd IN ('ON', 'OFF')
  AND ie.d1_removal_dttm IS NULL
  AND ie.install_evt_id NOT LIKE 'ODEV%'
  AND prem.address1 IS NULL
ORDER BY ie.install_evt_id
FETCH FIRST 100 ROWS ONLY;
