-- Post-load validation: 5 meter install events (ON/OFF) on ODEV service points.
PROMPT === Pack M01 meter validation (failure rows only) ===

SELECT check_id, detail, expected_value, actual_value
FROM (
  SELECT 'm01_install_count' AS check_id,
         'Expected 5 ODEV install events' AS detail,
         '5' AS expected_value,
         TO_CHAR(COUNT(*)) AS actual_value
    FROM cisadm.d1_install_evt
   WHERE install_evt_id LIKE 'ODEV%M%'
  HAVING COUNT(*) <> 5

  UNION ALL
  SELECT 'm01_on_count',
         'Expected 3 install events ON',
         '3',
         TO_CHAR(COUNT(*))
    FROM cisadm.d1_install_evt
   WHERE install_evt_id LIKE 'ODEV%M%'
     AND bo_status_cd = 'ON'
  HAVING COUNT(*) <> 3

  UNION ALL
  SELECT 'm01_off_count',
         'Expected 2 install events OFF',
         '2',
         TO_CHAR(COUNT(*))
    FROM cisadm.d1_install_evt
   WHERE install_evt_id LIKE 'ODEV%M%'
     AND bo_status_cd = 'OFF'
  HAVING COUNT(*) <> 2

  UNION ALL
  SELECT 'm01_sp_link',
         'Install events must point at ODEV CI_SP ids',
         '5',
         TO_CHAR(COUNT(*))
    FROM cisadm.d1_install_evt ie
   WHERE ie.install_evt_id LIKE 'ODEV%M%'
     AND ie.d1_sp_id IN ('ODEV010005','ODEV210005','ODEV310005','ODEV410005','ODEV510005')
  HAVING COUNT(*) <> 5
)
ORDER BY check_id;
