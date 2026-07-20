-- Pack M01: five meter install events on ODEV service points (3 ON, 2 OFF).
-- Links install_evt.d1_sp_id to CI_SP.sp_id (device snapshot join pattern).
--
-- Run after billing customers exist (10 + 11 scripts):
--   python3 scripts/local/run_client_oracle_sql.py --client odessa_dev \
--     --file sql/odessa_dev/test_data/20_pack_m01_meter_five.sql --fail-if-any-rows

PROMPT === Pack M01 meter preflight ===

SELECT check_id, detail, metric
FROM (
  SELECT 'preflight_meter_exists' AS check_id,
         'Meter row already loaded' AS detail,
         install_evt_id AS metric
    FROM cisadm.d1_install_evt
   WHERE install_evt_id LIKE 'ODEV%M%'
     AND ROWNUM = 1

  UNION ALL
  SELECT 'preflight_sp_missing',
         'ODEV CI_SP missing for meters',
         req.sp_id
    FROM (
      SELECT 'ODEV010005' AS sp_id FROM dual UNION ALL
      SELECT 'ODEV210005' FROM dual UNION ALL
      SELECT 'ODEV310005' FROM dual UNION ALL
      SELECT 'ODEV410005' FROM dual UNION ALL
      SELECT 'ODEV510005' FROM dual
    ) req
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_sp sp WHERE sp.sp_id = req.sp_id)

  UNION ALL
  SELECT 'preflight_template_install',
         'Golden install event missing',
         '0'
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1 FROM cisadm.d1_install_evt WHERE install_evt_id = '947939843894'
         )
)
ORDER BY check_id;

DECLARE
@@lib/clone_type.sql

  c_tpl_dvc    CONSTANT VARCHAR2(12) := '947843036120';
  c_tpl_cfg    CONSTANT VARCHAR2(12) := '947551615475';
  c_tpl_mc     CONSTANT VARCHAR2(12) := '947845858291';
  c_tpl_d1_sp  CONSTANT VARCHAR2(12) := '080128033008';
  c_tpl_ie     CONSTANT VARCHAR2(12) := '947939843894';

  TYPE t_mid IS TABLE OF PLS_INTEGER;
  TYPE t_stat IS TABLE OF VARCHAR2(4);
  c_mids  t_mid  := t_mid(1, 21, 31, 41, 51);
  c_stats t_stat := t_stat('ON', 'ON', 'OFF', 'ON', 'OFF');

  o        t_override_map;
  l_rows   NUMBER;
  l_cnt    NUMBER;
  l_mid    PLS_INTEGER;
  l_sp     VARCHAR2(10);
  l_dvc    VARCHAR2(12);
  l_cfg    VARCHAR2(12);
  l_mc     VARCHAR2(12);
  l_ie     VARCHAR2(12);

@@lib/clone_procedures.sql

  FUNCTION id10(p_mid PLS_INTEGER, p_slot PLS_INTEGER) RETURN VARCHAR2 IS
  BEGIN
    RETURN 'ODEV' || LPAD(p_mid, 2, '0') || LPAD(p_slot, 4, '0');
  END id10;

  FUNCTION meter_id(p_mid PLS_INTEGER, p_kind VARCHAR2) RETURN VARCHAR2 IS
  BEGIN
    RETURN 'ODEV' || LPAD(p_mid, 2, '0') || p_kind || '00001';
  END meter_id;

  PROCEDURE load_meter(p_mid PLS_INTEGER, p_status VARCHAR2) IS
  BEGIN
    l_sp  := id10(p_mid, 5);
    l_dvc := meter_id(p_mid, 'D');
    l_cfg := meter_id(p_mid, 'C');
    l_mc  := meter_id(p_mid, 'K');
    l_ie  := meter_id(p_mid, 'M');

    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_sp WHERE sp_id = ''' || l_sp || '''',
      1,
      'CI_SP prerequisite ' || l_sp
    );

    clear_overrides(o);
    set_override(o, 'D1_DEVICE_ID', '''' || l_dvc || '''');
    insert_clone('D1_DVC', 'd1_device_id = ''' || c_tpl_dvc || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'DEVICE_CONFIG_ID', '''' || l_cfg || '''');
    set_override(o, 'D1_DEVICE_ID', '''' || l_dvc || '''');
    insert_clone('D1_DVC_CFG', 'device_config_id = ''' || c_tpl_cfg || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'MEASR_COMP_ID', '''' || l_mc || '''');
    set_override(o, 'DEVICE_CONFIG_ID', '''' || l_cfg || '''');
    insert_clone('D1_MEASR_COMP', 'measr_comp_id = ''' || c_tpl_mc || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'D1_SP_ID', '''' || l_sp || '''');
    insert_clone('D1_SP', 'd1_sp_id = ''' || c_tpl_d1_sp || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'INSTALL_EVT_ID', '''' || l_ie || '''');
    set_override(o, 'D1_SP_ID', '''' || l_sp || '''');
    set_override(o, 'DEVICE_CONFIG_ID', '''' || l_cfg || '''');
    set_override(o, 'BO_STATUS_CD', '''' || p_status || '''');
    set_override(o, 'D1_INSTALL_DTTM', 'SYSTIMESTAMP - 30');
    IF p_status = 'OFF' THEN
      set_override(o, 'D1_REMOVAL_DTTM', 'SYSTIMESTAMP - 1');
    ELSE
      set_override(o, 'D1_REMOVAL_DTTM', 'NULL');
    END IF;
    set_override(o, 'STATUS_UPD_DTTM', 'SYSTIMESTAMP');
    insert_clone('D1_INSTALL_EVT', 'install_evt_id = ''' || c_tpl_ie || '''', o, l_rows);

    assert_count_eq(
      'SELECT 1 FROM cisadm.d1_install_evt WHERE install_evt_id = ''' || l_ie || ''' AND bo_status_cd = ''' || p_status || '''',
      1,
      'D1_INSTALL_EVT ' || l_ie || ' status ' || p_status
    );
  END load_meter;

BEGIN
  SELECT COUNT(*) INTO l_cnt FROM cisadm.d1_install_evt WHERE install_evt_id LIKE 'ODEV%M%';
  assert_true(l_cnt = 0, 'ODEV meter rows already exist');

  FOR i IN 1 .. c_mids.COUNT LOOP
    load_meter(c_mids(i), c_stats(i));
  END LOOP;

  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END;
/

@@lib/validate_m01_post_load.sql
