-- FAIL gate: latest on/off history is OFF (D1OF), no removal date, but install status is not OFF.
-- C2M: meter still at SP but turned off => BO_STATUS_CD should be OFF.
-- Reference: CityCorp has hundreds of OFF + D1OF + no removal.

PROMPT === Gate 01: install event Off alignment (failure rows only) ===

WITH latest AS (
  SELECT install_evt_id,
         onoff_hist_flg,
         ROW_NUMBER() OVER (
           PARTITION BY install_evt_id
           ORDER BY evt_dttm DESC, seqno DESC
         ) AS rn
  FROM cisadm.d1_on_off_hist
)
SELECT '01_off_hist_status_mismatch' AS check_id,
       'FAIL' AS severity,
       ie.install_evt_id,
       ie.bo_status_cd AS actual_status,
       'OFF' AS expected_status,
       l.onoff_hist_flg AS latest_onoff,
       ie.d1_sp_id,
       ie.d1_removal_dttm
FROM cisadm.d1_install_evt ie
JOIN latest l
  ON l.install_evt_id = ie.install_evt_id
 AND l.rn = 1
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND l.onoff_hist_flg = 'D1OF'
  AND ie.d1_removal_dttm IS NULL
  AND ie.bo_status_cd <> 'OFF'
  AND ie.install_evt_id NOT LIKE 'ODEV%'
ORDER BY ie.install_evt_id
FETCH FIRST 100 ROWS ONLY;
