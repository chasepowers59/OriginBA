-- Post-load validation for pack B01 (failure rows only).
-- Pair with: --fail-if-any-rows on the SQL runner for a hard gate.

PROMPT === Pack B01 post-load validation (empty result = PASS) ===

SELECT check_id,
       detail,
       expected_value,
       actual_value
FROM (
  SELECT 'b01_ci_per' AS check_id,
         'CI_PER row missing' AS detail,
         '1' AS expected_value,
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_per WHERE per_id = 'ODEV010001')) AS actual_value
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_per WHERE per_id = 'ODEV010001')

  UNION ALL
  SELECT 'b01_ci_per_name',
         'CI_PER_NAME primary name missing or wrong',
         'ODEV TEST B01 CUSTOMER 0001',
         (SELECT MAX(entity_name) FROM cisadm.ci_per_name WHERE per_id = 'ODEV010001' AND prim_name_sw = 'Y')
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1
             FROM cisadm.ci_per_name
            WHERE per_id = 'ODEV010001'
              AND prim_name_sw = 'Y'
              AND entity_name = 'ODEV TEST B01 CUSTOMER 0001'
         )

  UNION ALL
  SELECT 'b01_ci_acct',
         'CI_ACCT row missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_acct WHERE acct_id = 'ODEV010002'))
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_acct WHERE acct_id = 'ODEV010002')

  UNION ALL
  SELECT 'b01_ci_acct_per',
         'CI_ACCT_PER main customer link missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_acct_per WHERE acct_id = 'ODEV010002' AND per_id = 'ODEV010001'))
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1
             FROM cisadm.ci_acct_per
            WHERE acct_id = 'ODEV010002'
              AND per_id = 'ODEV010001'
              AND main_cust_sw = 'Y'
         )

  UNION ALL
  SELECT 'b01_ci_sa',
         'CI_SA row missing or wrong premise',
         'char_prem_id=ODEV010003',
         (SELECT char_prem_id FROM cisadm.ci_sa WHERE sa_id = 'ODEV010004')
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1
             FROM cisadm.ci_sa
            WHERE sa_id = 'ODEV010004'
              AND acct_id = 'ODEV010002'
              AND char_prem_id = 'ODEV010003'
              AND sa_type_cd = 'W-RES'
              AND sa_status_flg = '20'
         )

  UNION ALL
  SELECT 'b01_ci_sp',
         'CI_SP row missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_sp WHERE sp_id = 'ODEV010005'))
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_sp WHERE sp_id = 'ODEV010005' AND prem_id = 'ODEV010003')

  UNION ALL
  SELECT 'b01_ci_sa_sp',
         'CI_SA_SP link missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_sa_sp WHERE sa_id = 'ODEV010004' AND sp_id = 'ODEV010005'))
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1 FROM cisadm.ci_sa_sp WHERE sa_id = 'ODEV010004' AND sp_id = 'ODEV010005'
         )

  UNION ALL
  SELECT 'b01_ci_bill',
         'CI_BILL row missing or bill cycle blank',
         'bill_cyc_cd=83',
         (SELECT TRIM(bill_cyc_cd) FROM cisadm.ci_bill WHERE bill_id = 'ODEV01000001')
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1
             FROM cisadm.ci_bill
            WHERE bill_id = 'ODEV01000001'
              AND acct_id = 'ODEV010002'
              AND bill_stat_flg = 'C '
              AND TRIM(bill_cyc_cd) = '83'
         )

  UNION ALL
  SELECT 'b01_ci_bseg',
         'CI_BSEG water segment missing or wrong status',
         'bseg_stat_flg=50',
         (SELECT bseg_stat_flg FROM cisadm.ci_bseg WHERE bseg_id = 'ODEV02000001')
    FROM dual
   WHERE NOT EXISTS (
           SELECT 1
             FROM cisadm.ci_bseg
            WHERE bseg_id = 'ODEV02000001'
              AND bill_id = 'ODEV01000001'
              AND sa_id = 'ODEV010004'
              AND bseg_stat_flg = '50'
         )

  UNION ALL
  SELECT 'b01_ci_bseg_calc',
         'CI_BSEG_CALC row missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_bseg_calc WHERE bseg_id = 'ODEV02000001'))
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_bseg_calc WHERE bseg_id = 'ODEV02000001')

  UNION ALL
  SELECT 'b01_ci_bseg_sq',
         'CI_BSEG_SQ row missing',
         '1',
         TO_CHAR((SELECT COUNT(*) FROM cisadm.ci_bseg_sq WHERE bseg_id = 'ODEV02000001'))
    FROM dual
   WHERE NOT EXISTS (SELECT 1 FROM cisadm.ci_bseg_sq WHERE bseg_id = 'ODEV02000001')

  UNION ALL
  SELECT 'b01_chain_integrity',
         'Billing chain join count not 1',
         '1',
         TO_CHAR((
           SELECT COUNT(*)
             FROM cisadm.ci_acct a
             JOIN cisadm.ci_acct_per ap ON ap.acct_id = a.acct_id AND ap.main_cust_sw = 'Y'
             JOIN cisadm.ci_per_name pn ON pn.per_id = ap.per_id AND pn.prim_name_sw = 'Y'
             JOIN cisadm.ci_sa sa ON sa.acct_id = a.acct_id
             JOIN cisadm.ci_sa_sp sasp ON sasp.sa_id = sa.sa_id
             JOIN cisadm.ci_sp sp ON sp.sp_id = sasp.sp_id AND sp.prem_id = sa.char_prem_id
             JOIN cisadm.ci_bill b ON b.acct_id = a.acct_id
             JOIN cisadm.ci_bseg bs ON bs.bill_id = b.bill_id AND bs.sa_id = sa.sa_id
            WHERE a.acct_id = 'ODEV010002'
              AND b.bill_id = 'ODEV01000001'
              AND bs.bseg_id = 'ODEV02000001'
         ))
    FROM dual
   WHERE (
           SELECT COUNT(*)
             FROM cisadm.ci_acct a
             JOIN cisadm.ci_acct_per ap ON ap.acct_id = a.acct_id AND ap.main_cust_sw = 'Y'
             JOIN cisadm.ci_per_name pn ON pn.per_id = ap.per_id AND pn.prim_name_sw = 'Y'
             JOIN cisadm.ci_sa sa ON sa.acct_id = a.acct_id
             JOIN cisadm.ci_sa_sp sasp ON sasp.sa_id = sa.sa_id
             JOIN cisadm.ci_sp sp ON sp.sp_id = sasp.sp_id AND sp.prem_id = sa.char_prem_id
             JOIN cisadm.ci_bill b ON b.acct_id = a.acct_id
             JOIN cisadm.ci_bseg bs ON bs.bill_id = b.bill_id AND bs.sa_id = sa.sa_id
            WHERE a.acct_id = 'ODEV010002'
              AND b.bill_id = 'ODEV01000001'
              AND bs.bseg_id = 'ODEV02000001'
         ) <> 1
)
ORDER BY check_id;
