-- FAIL gate: account has bill cycle but bill header is blank (Odessa conversion gap).

PROMPT === Gate 05: bill cycle on bill header (summary) ===

SELECT '05_bill_cycle_header_blank' AS check_id,
       'FAIL' AS severity,
       COUNT(*) AS failure_cnt
FROM cisadm.ci_bill b
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id
WHERE TRIM(a.bill_cyc_cd) IS NOT NULL
  AND TRIM(b.bill_cyc_cd) IS NULL
  AND b.acct_id NOT LIKE 'ODEV%'
HAVING COUNT(*) > 0;

PROMPT === Gate 05: bill cycle on bill header (failure sample) ===

SELECT '05_bill_cycle_header_blank' AS check_id,
       'FAIL' AS severity,
       b.bill_id,
       b.acct_id,
       TRIM(a.bill_cyc_cd) AS acct_bill_cyc,
       TRIM(b.bill_cyc_cd) AS bill_bill_cyc,
       b.bill_dt
FROM cisadm.ci_bill b
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id
WHERE TRIM(a.bill_cyc_cd) IS NOT NULL
  AND TRIM(b.bill_cyc_cd) IS NULL
  AND b.acct_id NOT LIKE 'ODEV%'
ORDER BY b.bill_dt DESC NULLS LAST
FETCH FIRST 25 ROWS ONLY;
