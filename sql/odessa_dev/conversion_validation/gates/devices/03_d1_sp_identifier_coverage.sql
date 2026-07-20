-- FAIL gate: active ON manual-meter installs missing D1_SP_IDENTIFIER (D1EI).
-- Blocks CMS_DVC_ACCT and premise joins in Jaspersoft device domains.

PROMPT === Gate 03: D1_SP_IDENTIFIER D1EI coverage (failure rows only) ===

SELECT '03_missing_d1ei_identifier' AS check_id,
       'FAIL' AS severity,
       ie.install_evt_id,
       ie.d1_sp_id,
       ie.bo_status_cd,
       ie.d1_install_dttm
FROM cisadm.d1_install_evt ie
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND ie.bo_status_cd = 'ON'
  AND ie.d1_removal_dttm IS NULL
  AND ie.install_evt_id NOT LIKE 'ODEV%'
  AND NOT EXISTS (
        SELECT 1
          FROM cisadm.d1_sp_identifier spid
         WHERE spid.d1_sp_id = ie.d1_sp_id
           AND spid.sp_id_type_flg = 'D1EI'
      )
ORDER BY ie.install_evt_id
FETCH FIRST 100 ROWS ONLY;
