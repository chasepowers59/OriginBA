-- WARN gate: no converted install events with status OFF (other clients have some).
-- Excludes ODEV synthetic rows.

PROMPT === Gate 02: install event OFF population (WARN if zero) ===

SELECT '02_no_converted_off_status' AS check_id,
       'WARN' AS severity,
       'Zero converted D1-ManualMeterInstallEvent rows with BO_STATUS_CD=OFF' AS detail,
       TO_CHAR(cnt) AS metric
FROM (
  SELECT COUNT(*) AS cnt
  FROM cisadm.d1_install_evt
  WHERE bus_obj_cd = 'D1-ManualMeterInstallEvent'
    AND bo_status_cd = 'OFF'
    AND install_evt_id NOT LIKE 'ODEV%'
)
WHERE cnt = 0;
