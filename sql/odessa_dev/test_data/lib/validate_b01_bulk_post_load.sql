-- Post-load validation: expect 5 ODEV billing accounts (customers 01 + 21/31/41/51).
PROMPT === Pack B01 bulk validation (failure rows only) ===

SELECT check_id, detail, expected_value, actual_value
FROM (
  SELECT 'b01_acct_count' AS check_id,
         'Expected 5 ODEV billing accounts' AS detail,
         '5' AS expected_value,
         TO_CHAR(COUNT(*)) AS actual_value
    FROM cisadm.ci_acct
   WHERE acct_id IN ('ODEV010002','ODEV210002','ODEV310002','ODEV410002','ODEV510002')
  HAVING COUNT(*) <> 5

  UNION ALL
  SELECT 'b01_bill_count',
         'Expected 5 ODEV bills with cycle 83',
         '5',
         TO_CHAR(COUNT(*))
    FROM cisadm.ci_bill
   WHERE acct_id IN ('ODEV010002','ODEV210002','ODEV310002','ODEV410002','ODEV510002')
     AND bill_stat_flg = 'C '
     AND TRIM(bill_cyc_cd) = '83'
  HAVING COUNT(*) <> 5

  UNION ALL
  SELECT 'b01_bseg_count',
         'Expected 5 ODEV water bsegs frozen',
         '5',
         TO_CHAR(COUNT(*))
    FROM cisadm.ci_bseg
   WHERE sa_id IN ('ODEV010004','ODEV210004','ODEV310004','ODEV410004','ODEV510004')
     AND bseg_stat_flg = '50'
  HAVING COUNT(*) <> 5
)
ORDER BY check_id;
