-- Pack B01: clone completed water billing chain + validate in one script.
--
-- Run (VPN on):
--   python3 scripts/local/run_client_oracle_sql.py \
--     --client odessa_dev \
--     --file sql/odessa_dev/test_data/10_pack_b01_billing_clone.sql \
--     --fail-if-any-rows
--
-- Sections:
--   1) Preflight gate (collision / template checks)
--   2) PL/SQL clone load with in-block assertions
--   3) Post-load SELECT validation (empty = pass with --fail-if-any-rows)

PROMPT === Pack B01 preflight (failure rows block load) ===

SELECT check_id, detail, metric
FROM (
  SELECT 'preflight_odev_collision' AS check_id,
         'Existing ODEV rows — run 99_rollback_odev.sql first' AS detail,
         TO_CHAR(total_cnt) AS metric
    FROM (
      SELECT SUM(cnt) AS total_cnt
        FROM (
          SELECT COUNT(*) AS cnt FROM cisadm.ci_per WHERE per_id LIKE 'ODEV%'
          UNION ALL SELECT COUNT(*) FROM cisadm.ci_acct WHERE acct_id LIKE 'ODEV%'
          UNION ALL SELECT COUNT(*) FROM cisadm.ci_bill WHERE bill_id LIKE 'ODEV%'
          UNION ALL SELECT COUNT(*) FROM cisadm.ci_bseg WHERE bseg_id LIKE 'ODEV%'
        )
    )
   WHERE total_cnt > 0

  UNION ALL
  SELECT 'preflight_template_acct',
         'Golden template account 1110100087 missing',
         '0'
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_acct WHERE acct_id = '1110100087')

  UNION ALL
  SELECT 'preflight_template_bseg',
         'Golden template bseg 776805100203 missing',
         '0'
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_bseg WHERE bseg_id = '776805100203')
)
ORDER BY check_id;

DECLARE
@@lib/clone_type.sql

  -- Golden template keys (read-only source — do not modify)
  c_tpl_per   CONSTANT VARCHAR2(32) := '9184027141';
  c_tpl_prem  CONSTANT VARCHAR2(32) := '4237790275';
  c_tpl_acct  CONSTANT VARCHAR2(32) := '1110100087';
  c_tpl_sa    CONSTANT VARCHAR2(32) := '7790352119';
  c_tpl_sp    CONSTANT VARCHAR2(32) := '8740115078';
  c_tpl_bill  CONSTANT VARCHAR2(48) := '856601546942';
  c_tpl_bseg  CONSTANT VARCHAR2(48) := '776805100203';

  -- New ODEV keys (CHAR(10) / CHAR(12) limits on pdevdb)
  c_new_per   CONSTANT VARCHAR2(10) := 'ODEV010001';
  c_new_prem  CONSTANT VARCHAR2(10) := 'ODEV010003';
  c_new_acct  CONSTANT VARCHAR2(10) := 'ODEV010002';
  c_new_sa    CONSTANT VARCHAR2(10) := 'ODEV010004';
  c_new_sp    CONSTANT VARCHAR2(10) := 'ODEV010005';
  c_new_sa_sp CONSTANT VARCHAR2(10) := 'ODEV040001';
  c_new_bill  CONSTANT VARCHAR2(12) := 'ODEV01000001';
  c_new_bseg  CONSTANT VARCHAR2(12) := 'ODEV02000001';

  c_display_name CONSTANT VARCHAR2(64) := 'ODEV TEST B01 CUSTOMER 0001';

  o           t_override_map;
  l_rows      NUMBER;
  l_cnt       NUMBER;
  l_tpl_ft    NUMBER;
  l_tpl_sa_ch NUMBER;
  l_tpl_ln    NUMBER;

@@lib/clone_procedures.sql

  PROCEDURE validate_in_block IS
  BEGIN
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_per WHERE per_id = ''' || c_new_per || '''',
      1,
      'CI_PER after insert'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_per_name WHERE per_id = ''' || c_new_per || ''' AND prim_name_sw = ''Y'' AND entity_name = ''' || c_display_name || '''',
      1,
      'CI_PER_NAME display name'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_acct WHERE acct_id = ''' || c_new_acct || '''',
      1,
      'CI_ACCT after insert'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_acct_per WHERE acct_id = ''' || c_new_acct || ''' AND per_id = ''' || c_new_per || ''' AND main_cust_sw = ''Y''',
      1,
      'CI_ACCT_PER link'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_prem WHERE prem_id = ''' || c_new_prem || '''',
      1,
      'CI_PREM after insert'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_sa WHERE sa_id = ''' || c_new_sa || ''' AND acct_id = ''' || c_new_acct || ''' AND char_prem_id = ''' || c_new_prem || '''',
      1,
      'CI_SA after insert'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_sp WHERE sp_id = ''' || c_new_sp || ''' AND prem_id = ''' || c_new_prem || '''',
      1,
      'CI_SP after insert'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_sa_sp WHERE sa_id = ''' || c_new_sa || ''' AND sp_id = ''' || c_new_sp || '''',
      1,
      'CI_SA_SP link'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_bill WHERE bill_id = ''' || c_new_bill || ''' AND acct_id = ''' || c_new_acct || ''' AND bill_stat_flg = ''C '' AND TRIM(bill_cyc_cd) = ''83''',
      1,
      'CI_BILL complete with bill cycle'
    );
    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_bseg WHERE bseg_id = ''' || c_new_bseg || ''' AND bill_id = ''' || c_new_bill || ''' AND sa_id = ''' || c_new_sa || ''' AND bseg_stat_flg = ''50''',
      1,
      'CI_BSEG frozen water segment'
    );
    assert_count_ge(
      'SELECT 1 FROM cisadm.ci_bseg_calc WHERE bseg_id = ''' || c_new_bseg || '''',
      1,
      'CI_BSEG_CALC'
    );
    assert_count_ge(
      'SELECT 1 FROM cisadm.ci_bseg_sq WHERE bseg_id = ''' || c_new_bseg || '''',
      1,
      'CI_BSEG_SQ'
    );
    assert_count_eq(
      'SELECT 1
         FROM cisadm.ci_acct a
         JOIN cisadm.ci_sa sa ON sa.acct_id = a.acct_id
         JOIN cisadm.ci_bill b ON b.acct_id = a.acct_id
         JOIN cisadm.ci_bseg bs ON bs.bill_id = b.bill_id AND bs.sa_id = sa.sa_id
        WHERE a.acct_id = ''' || c_new_acct || '''
          AND b.bill_id = ''' || c_new_bill || '''
          AND bs.bseg_id = ''' || c_new_bseg || '''',
      1,
      'billing chain integrity'
    );
  END validate_in_block;

BEGIN
  -- Hard stop if preflight would fail (same rules as SELECT gate above).
  SELECT SUM(cnt)
    INTO l_cnt
    FROM (
      SELECT COUNT(*) AS cnt FROM cisadm.ci_per WHERE per_id LIKE 'ODEV%'
      UNION ALL SELECT COUNT(*) FROM cisadm.ci_acct WHERE acct_id LIKE 'ODEV%'
      UNION ALL SELECT COUNT(*) FROM cisadm.ci_bill WHERE bill_id LIKE 'ODEV%'
      UNION ALL SELECT COUNT(*) FROM cisadm.ci_bseg WHERE bseg_id LIKE 'ODEV%'
    );
  assert_true(l_cnt = 0, 'ODEV collision — rollback existing ODEV rows before load');

  SELECT COUNT(*) INTO l_cnt FROM cisadm.ci_acct WHERE acct_id = c_tpl_acct;
  assert_true(l_cnt = 1, 'Template account ' || c_tpl_acct || ' not found');

  SELECT COUNT(*) INTO l_cnt FROM cisadm.ci_bseg WHERE bseg_id = c_tpl_bseg;
  assert_true(l_cnt = 1, 'Template bseg ' || c_tpl_bseg || ' not found');

  -- 1) CI_PER
  clear_overrides(o);
  set_override(o, 'PER_ID', '''' || c_new_per || '''');
  insert_clone('CI_PER', 'per_id = ''' || c_tpl_per || '''', o, l_rows);
  assert_count_eq('SELECT 1 FROM cisadm.ci_per WHERE per_id = ''' || c_new_per || '''', 1, 'CI_PER insert rowcount');

  -- 2) CI_PER_NAME (all name rows for person)
  FOR rec IN (
    SELECT name_type_flg, prim_name_sw
      FROM cisadm.ci_per_name
     WHERE per_id = c_tpl_per
  ) LOOP
    clear_overrides(o);
    set_override(o, 'PER_ID', '''' || c_new_per || '''');
    IF rec.prim_name_sw = 'Y' THEN
      set_override(o, 'ENTITY_NAME', '''' || c_display_name || '''');
      set_override(o, 'ENTITY_NAME_UPR', '''' || UPPER(c_display_name) || '''');
    END IF;
    insert_clone(
      'CI_PER_NAME',
      'per_id = ''' || c_tpl_per || ''' AND name_type_flg = ''' || rec.name_type_flg || '''',
      o,
      l_rows
    );
  END LOOP;

  -- 3) CI_PREM
  clear_overrides(o);
  set_override(o, 'PREM_ID', '''' || c_new_prem || '''');
  insert_clone('CI_PREM', 'prem_id = ''' || c_tpl_prem || '''', o, l_rows);
  assert_count_eq('SELECT 1 FROM cisadm.ci_prem WHERE prem_id = ''' || c_new_prem || '''', 1, 'CI_PREM insert');

  -- 4) CI_ACCT
  clear_overrides(o);
  set_override(o, 'ACCT_ID', '''' || c_new_acct || '''');
  insert_clone('CI_ACCT', 'acct_id = ''' || c_tpl_acct || '''', o, l_rows);

  -- 5) CI_ACCT_PER
  clear_overrides(o);
  set_override(o, 'ACCT_ID', '''' || c_new_acct || '''');
  set_override(o, 'PER_ID', '''' || c_new_per || '''');
  insert_clone(
    'CI_ACCT_PER',
    'acct_id = ''' || c_tpl_acct || ''' AND per_id = ''' || c_tpl_per || '''',
    o,
    l_rows
  );

  -- 6) CI_SA
  clear_overrides(o);
  set_override(o, 'SA_ID', '''' || c_new_sa || '''');
  set_override(o, 'ACCT_ID', '''' || c_new_acct || '''');
  set_override(o, 'CHAR_PREM_ID', '''' || c_new_prem || '''');
  insert_clone('CI_SA', 'sa_id = ''' || c_tpl_sa || '''', o, l_rows);

  -- 7) CI_SA_CHAR (optional on template)
  SELECT COUNT(*) INTO l_tpl_sa_ch FROM cisadm.ci_sa_char WHERE sa_id = c_tpl_sa;
  IF l_tpl_sa_ch > 0 THEN
    FOR rec IN (
      SELECT char_type_cd
        FROM cisadm.ci_sa_char
       WHERE sa_id = c_tpl_sa
    ) LOOP
      clear_overrides(o);
      set_override(o, 'SA_ID', '''' || c_new_sa || '''');
      insert_clone(
        'CI_SA_CHAR',
        'sa_id = ''' || c_tpl_sa || ''' AND char_type_cd = ''' || rec.char_type_cd || '''',
        o,
        l_rows
      );
    END LOOP;
  END IF;

  -- 8) CI_SP
  clear_overrides(o);
  set_override(o, 'SP_ID', '''' || c_new_sp || '''');
  set_override(o, 'PREM_ID', '''' || c_new_prem || '''');
  insert_clone('CI_SP', 'sp_id = ''' || c_tpl_sp || '''', o, l_rows);

  -- 9) CI_SA_SP
  clear_overrides(o);
  set_override(o, 'SA_SP_ID', '''' || c_new_sa_sp || '''');
  set_override(o, 'SA_ID', '''' || c_new_sa || '''');
  set_override(o, 'SP_ID', '''' || c_new_sp || '''');
  insert_clone(
    'CI_SA_SP',
    'sa_id = ''' || c_tpl_sa || ''' AND sp_id = ''' || c_tpl_sp || '''',
    o,
    l_rows
  );

  -- 10) CI_BILL (stamp bill cycle from account — Odessa conversion gap)
  clear_overrides(o);
  set_override(o, 'BILL_ID', '''' || c_new_bill || '''');
  set_override(o, 'ACCT_ID', '''' || c_new_acct || '''');
  set_override(o, 'BILL_CYC_CD', '(SELECT bill_cyc_cd FROM cisadm.ci_acct WHERE acct_id = ''' || c_new_acct || ''')');
  set_override(o, 'BILL_DT', 'TRUNC(SYSDATE) - 1');
  set_override(o, 'DUE_DT', 'TRUNC(SYSDATE) + 21');
  set_override(o, 'CRE_DTTM', 'SYSDATE');
  set_override(o, 'COMPLETE_DTTM', 'SYSDATE');
  insert_clone('CI_BILL', 'bill_id = ''' || c_tpl_bill || '''', o, l_rows);

  -- 11) CI_BSEG (water segment only)
  clear_overrides(o);
  set_override(o, 'BSEG_ID', '''' || c_new_bseg || '''');
  set_override(o, 'BILL_ID', '''' || c_new_bill || '''');
  set_override(o, 'SA_ID', '''' || c_new_sa || '''');
  set_override(o, 'START_DT', 'TRUNC(SYSDATE) - 31');
  set_override(o, 'END_DT', 'TRUNC(SYSDATE) - 1');
  set_override(o, 'CRE_DTTM', 'SYSDATE');
  insert_clone('CI_BSEG', 'bseg_id = ''' || c_tpl_bseg || '''', o, l_rows);

  -- 12) CI_BSEG_CALC
  clear_overrides(o);
  set_override(o, 'BSEG_ID', '''' || c_new_bseg || '''');
  insert_clone('CI_BSEG_CALC', 'bseg_id = ''' || c_tpl_bseg || '''', o, l_rows);

  -- 12b) CI_BSEG_CALC_LN (if template has lines)
  SELECT COUNT(*) INTO l_tpl_ln FROM cisadm.ci_bseg_calc_ln WHERE bseg_id = c_tpl_bseg;
  IF l_tpl_ln > 0 THEN
    FOR rec IN (
      SELECT header_seq, seqno
        FROM cisadm.ci_bseg_calc_ln
       WHERE bseg_id = c_tpl_bseg
       ORDER BY header_seq, seqno
    ) LOOP
      clear_overrides(o);
      set_override(o, 'BSEG_ID', '''' || c_new_bseg || '''');
      insert_clone(
        'CI_BSEG_CALC_LN',
        'bseg_id = ''' || c_tpl_bseg || ''' AND header_seq = ' || rec.header_seq || ' AND seqno = ' || rec.seqno,
        o,
        l_rows
      );
    END LOOP;
  END IF;

  -- 13) CI_BSEG_SQ (PK: bseg_id + uom_cd + tou_cd + sqi_cd)
  FOR rec IN (
    SELECT uom_cd, tou_cd, sqi_cd
      FROM cisadm.ci_bseg_sq
     WHERE bseg_id = c_tpl_bseg
     ORDER BY uom_cd, tou_cd, sqi_cd
  ) LOOP
    clear_overrides(o);
    set_override(o, 'BSEG_ID', '''' || c_new_bseg || '''');
    insert_clone(
      'CI_BSEG_SQ',
      'bseg_id = ''' || c_tpl_bseg || ''''
        || ' AND uom_cd = ''' || rec.uom_cd || ''''
        || ' AND tou_cd = ''' || rec.tou_cd || ''''
        || ' AND sqi_cd = ''' || rec.sqi_cd || '''',
      o,
      l_rows
    );
  END LOOP;

  -- 14) CI_FT (water SA rows only on template bill)
  SELECT COUNT(*) INTO l_tpl_ft
    FROM cisadm.ci_ft
   WHERE bill_id = c_tpl_bill
     AND sa_id = c_tpl_sa;
  IF l_tpl_ft > 0 THEN
    FOR rec IN (
      SELECT ft_id,
             sibling_id,
             parent_id,
             ROW_NUMBER() OVER (ORDER BY ft_id) AS rn
        FROM cisadm.ci_ft
       WHERE bill_id = c_tpl_bill
         AND sa_id = c_tpl_sa
    ) LOOP
      clear_overrides(o);
      set_override(o, 'FT_ID', '''ODEV03' || LPAD(TO_CHAR(rec.rn), 6, '0') || '''');
      set_override(o, 'BILL_ID', '''' || c_new_bill || '''');
      set_override(o, 'SA_ID', '''' || c_new_sa || '''');
      IF rec.sibling_id = c_tpl_bseg THEN
        set_override(o, 'SIBLING_ID', '''' || c_new_bseg || '''');
      END IF;
      IF rec.parent_id = c_tpl_bill THEN
        set_override(o, 'PARENT_ID', '''' || c_new_bill || '''');
      ELSIF rec.parent_id = c_tpl_bseg THEN
        set_override(o, 'PARENT_ID', '''' || c_new_bseg || '''');
      END IF;
      insert_clone('CI_FT', 'ft_id = ''' || rec.ft_id || '''', o, l_rows);
    END LOOP;
  END IF;

  validate_in_block;

  COMMIT;
  DBMS_OUTPUT.PUT_LINE('Pack B01 load committed successfully.');
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END;
/

@@lib/validate_b01_post_load.sql

PROMPT === Optional: refresh billed-usage snapshots after load ===
PROMPT EXEC cisadm.refresh_bseg_sq_usage_rpt_curr;
PROMPT EXEC cisadm.refresh_bseg_billed_usage_rpt_curr;
