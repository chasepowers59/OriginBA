-- Pack B01: add billing customers 2-5 (customer 1 already loaded as ODEV01xxxx).
-- Customer index map: 2->21, 3->31, 4->41, 5->51 (avoids ODEV040001 sa_sp collision on cust 1).
--
-- Run:
--   python3 scripts/local/run_client_oracle_sql.py --client odessa_dev \
--     --file sql/odessa_dev/test_data/11_pack_b01_add_customers_2_5.sql --fail-if-any-rows

PROMPT === Pack B01 add customers 2-5 preflight ===

SELECT check_id, detail, metric
FROM (
  SELECT 'preflight_cust2_exists' AS check_id,
         'Customer 2 already loaded' AS detail,
         acct_id AS metric
    FROM cisadm.ci_acct
   WHERE acct_id = 'ODEV210002'

  UNION ALL
  SELECT 'preflight_template_acct',
         'Golden template account missing',
         '0'
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_acct WHERE acct_id = '1110100087')
)
ORDER BY check_id;

DECLARE
@@lib/clone_type.sql

  c_tpl_per   CONSTANT VARCHAR2(10) := '9184027141';
  c_tpl_prem  CONSTANT VARCHAR2(10) := '4237790275';
  c_tpl_acct  CONSTANT VARCHAR2(10) := '1110100087';
  c_tpl_sa    CONSTANT VARCHAR2(10) := '7790352119';
  c_tpl_sp    CONSTANT VARCHAR2(10) := '8740115078';
  c_tpl_bill  CONSTANT VARCHAR2(12) := '856601546942';
  c_tpl_bseg  CONSTANT VARCHAR2(12) := '776805100203';

  TYPE t_cust_mid IS TABLE OF PLS_INTEGER;
  c_cust_mids  t_cust_mid := t_cust_mid(21, 31, 41, 51);

  o           t_override_map;
  l_rows      NUMBER;
  l_cnt       NUMBER;
  l_tpl_ft    NUMBER;
  l_tpl_sa_ch NUMBER;
  l_tpl_ln    NUMBER;
  l_mid       PLS_INTEGER;
  l_per       VARCHAR2(10);
  l_acct      VARCHAR2(10);
  l_prem      VARCHAR2(10);
  l_sa        VARCHAR2(10);
  l_sp        VARCHAR2(10);
  l_sa_sp     VARCHAR2(10);
  l_bill      VARCHAR2(12);
  l_bseg      VARCHAR2(12);
  l_name      VARCHAR2(64);
  l_cust_seq  PLS_INTEGER;

@@lib/clone_procedures.sql

  FUNCTION id10(p_mid PLS_INTEGER, p_slot PLS_INTEGER) RETURN VARCHAR2 IS
  BEGIN
    RETURN 'ODEV' || LPAD(p_mid, 2, '0') || LPAD(p_slot, 4, '0');
  END id10;

  FUNCTION id12(p_mid PLS_INTEGER, p_slot PLS_INTEGER) RETURN VARCHAR2 IS
  BEGIN
    RETURN 'ODEV' || LPAD(p_mid, 2, '0') || LPAD(p_slot, 6, '0');
  END id12;

  PROCEDURE load_customer(p_mid PLS_INTEGER, p_cust_seq PLS_INTEGER) IS
  BEGIN
    l_per   := id10(p_mid, 1);
    l_acct  := id10(p_mid, 2);
    l_prem  := id10(p_mid, 3);
    l_sa    := id10(p_mid, 4);
    l_sp    := id10(p_mid, 5);
    l_sa_sp := id10(p_mid, 6);
    l_bill  := id12(p_mid, 1);
    l_bseg  := id12(p_mid, 2);
    l_name  := 'ODEV TEST B01 CUSTOMER ' || LPAD(p_cust_seq, 4, '0');

    clear_overrides(o);
    set_override(o, 'PER_ID', '''' || l_per || '''');
    insert_clone('CI_PER', 'per_id = ''' || c_tpl_per || '''', o, l_rows);

    FOR rec IN (
      SELECT name_type_flg, prim_name_sw
        FROM cisadm.ci_per_name
       WHERE per_id = c_tpl_per
    ) LOOP
      clear_overrides(o);
      set_override(o, 'PER_ID', '''' || l_per || '''');
      IF rec.prim_name_sw = 'Y' THEN
        set_override(o, 'ENTITY_NAME', '''' || l_name || '''');
        set_override(o, 'ENTITY_NAME_UPR', '''' || UPPER(l_name) || '''');
      END IF;
      insert_clone(
        'CI_PER_NAME',
        'per_id = ''' || c_tpl_per || ''' AND name_type_flg = ''' || rec.name_type_flg || '''',
        o,
        l_rows
      );
    END LOOP;

    clear_overrides(o);
    set_override(o, 'PREM_ID', '''' || l_prem || '''');
    insert_clone('CI_PREM', 'prem_id = ''' || c_tpl_prem || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'ACCT_ID', '''' || l_acct || '''');
    insert_clone('CI_ACCT', 'acct_id = ''' || c_tpl_acct || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'ACCT_ID', '''' || l_acct || '''');
    set_override(o, 'PER_ID', '''' || l_per || '''');
    insert_clone(
      'CI_ACCT_PER',
      'acct_id = ''' || c_tpl_acct || ''' AND per_id = ''' || c_tpl_per || '''',
      o,
      l_rows
    );

    clear_overrides(o);
    set_override(o, 'SA_ID', '''' || l_sa || '''');
    set_override(o, 'ACCT_ID', '''' || l_acct || '''');
    set_override(o, 'CHAR_PREM_ID', '''' || l_prem || '''');
    insert_clone('CI_SA', 'sa_id = ''' || c_tpl_sa || '''', o, l_rows);

    SELECT COUNT(*) INTO l_tpl_sa_ch FROM cisadm.ci_sa_char WHERE sa_id = c_tpl_sa;
    IF l_tpl_sa_ch > 0 THEN
      FOR rec IN (SELECT char_type_cd FROM cisadm.ci_sa_char WHERE sa_id = c_tpl_sa) LOOP
        clear_overrides(o);
        set_override(o, 'SA_ID', '''' || l_sa || '''');
        insert_clone(
          'CI_SA_CHAR',
          'sa_id = ''' || c_tpl_sa || ''' AND char_type_cd = ''' || rec.char_type_cd || '''',
          o,
          l_rows
        );
      END LOOP;
    END IF;

    clear_overrides(o);
    set_override(o, 'SP_ID', '''' || l_sp || '''');
    set_override(o, 'PREM_ID', '''' || l_prem || '''');
    insert_clone('CI_SP', 'sp_id = ''' || c_tpl_sp || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'SA_SP_ID', '''' || l_sa_sp || '''');
    set_override(o, 'SA_ID', '''' || l_sa || '''');
    set_override(o, 'SP_ID', '''' || l_sp || '''');
    insert_clone(
      'CI_SA_SP',
      'sa_id = ''' || c_tpl_sa || ''' AND sp_id = ''' || c_tpl_sp || '''',
      o,
      l_rows
    );

    clear_overrides(o);
    set_override(o, 'BILL_ID', '''' || l_bill || '''');
    set_override(o, 'ACCT_ID', '''' || l_acct || '''');
    set_override(o, 'BILL_CYC_CD', '(SELECT bill_cyc_cd FROM cisadm.ci_acct WHERE acct_id = ''' || l_acct || ''')');
    set_override(o, 'BILL_DT', 'TRUNC(SYSDATE) - 1');
    set_override(o, 'DUE_DT', 'TRUNC(SYSDATE) + 21');
    set_override(o, 'CRE_DTTM', 'SYSDATE');
    set_override(o, 'COMPLETE_DTTM', 'SYSDATE');
    insert_clone('CI_BILL', 'bill_id = ''' || c_tpl_bill || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'BSEG_ID', '''' || l_bseg || '''');
    set_override(o, 'BILL_ID', '''' || l_bill || '''');
    set_override(o, 'SA_ID', '''' || l_sa || '''');
    set_override(o, 'START_DT', 'TRUNC(SYSDATE) - 31');
    set_override(o, 'END_DT', 'TRUNC(SYSDATE) - 1');
    set_override(o, 'CRE_DTTM', 'SYSDATE');
    insert_clone('CI_BSEG', 'bseg_id = ''' || c_tpl_bseg || '''', o, l_rows);

    clear_overrides(o);
    set_override(o, 'BSEG_ID', '''' || l_bseg || '''');
    insert_clone('CI_BSEG_CALC', 'bseg_id = ''' || c_tpl_bseg || '''', o, l_rows);

    SELECT COUNT(*) INTO l_tpl_ln FROM cisadm.ci_bseg_calc_ln WHERE bseg_id = c_tpl_bseg;
    IF l_tpl_ln > 0 THEN
      FOR rec IN (
        SELECT header_seq, seqno FROM cisadm.ci_bseg_calc_ln WHERE bseg_id = c_tpl_bseg
      ) LOOP
        clear_overrides(o);
        set_override(o, 'BSEG_ID', '''' || l_bseg || '''');
        insert_clone(
          'CI_BSEG_CALC_LN',
          'bseg_id = ''' || c_tpl_bseg || ''' AND header_seq = ' || rec.header_seq || ' AND seqno = ' || rec.seqno,
          o,
          l_rows
        );
      END LOOP;
    END IF;

    FOR rec IN (
      SELECT uom_cd, tou_cd, sqi_cd FROM cisadm.ci_bseg_sq WHERE bseg_id = c_tpl_bseg
    ) LOOP
      clear_overrides(o);
      set_override(o, 'BSEG_ID', '''' || l_bseg || '''');
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

    SELECT COUNT(*) INTO l_tpl_ft
      FROM cisadm.ci_ft WHERE bill_id = c_tpl_bill AND sa_id = c_tpl_sa;
    IF l_tpl_ft > 0 THEN
      FOR rec IN (
        SELECT ft_id, sibling_id, parent_id, ROW_NUMBER() OVER (ORDER BY ft_id) AS rn
          FROM cisadm.ci_ft WHERE bill_id = c_tpl_bill AND sa_id = c_tpl_sa
      ) LOOP
        clear_overrides(o);
        set_override(o, 'FT_ID', '''' || id12(p_mid, 2 + rec.rn) || '''');
        set_override(o, 'BILL_ID', '''' || l_bill || '''');
        set_override(o, 'SA_ID', '''' || l_sa || '''');
        IF rec.sibling_id = c_tpl_bseg THEN
          set_override(o, 'SIBLING_ID', '''' || l_bseg || '''');
        END IF;
        IF rec.parent_id = c_tpl_bill THEN
          set_override(o, 'PARENT_ID', '''' || l_bill || '''');
        ELSIF rec.parent_id = c_tpl_bseg THEN
          set_override(o, 'PARENT_ID', '''' || l_bseg || '''');
        END IF;
        insert_clone('CI_FT', 'ft_id = ''' || rec.ft_id || '''', o, l_rows);
      END LOOP;
    END IF;

    assert_count_eq(
      'SELECT 1 FROM cisadm.ci_acct WHERE acct_id = ''' || l_acct || '''',
      1,
      'CI_ACCT customer mid ' || p_mid
    );
  END load_customer;

BEGIN
  SELECT COUNT(*) INTO l_cnt FROM cisadm.ci_acct WHERE acct_id = 'ODEV210002';
  assert_true(l_cnt = 0, 'Customer 2 (ODEV210002) already exists');

  l_cust_seq := 2;
  FOR i IN 1 .. c_cust_mids.COUNT LOOP
    load_customer(c_cust_mids(i), l_cust_seq);
    l_cust_seq := l_cust_seq + 1;
  END LOOP;

  COMMIT;
EXCEPTION
  WHEN OTHERS THEN
    ROLLBACK;
    RAISE;
END;
/

@@lib/validate_b01_bulk_post_load.sql
