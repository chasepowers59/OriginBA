-- Read-only bill cycle source audit (run on CityCorp for QA; Odessa DEV for deploy validation).
-- No DDL/DML — safe on reference clients.

PROMPT === Source: CI_BILL complete bills ===

SELECT COUNT(*) AS bill_rows,
       SUM(CASE WHEN TRIM(b.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_header_populated,
       SUM(CASE WHEN TRIM(a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS acct_populated,
       SUM(CASE WHEN TRIM(a.bill_cyc_cd) IS NOT NULL AND TRIM(b.bill_cyc_cd) IS NULL THEN 1 ELSE 0 END) AS acct_only_gap
FROM cisadm.ci_bill b
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id
WHERE b.bill_stat_flg = 'C ';

PROMPT === Source: CI_BSEG on complete bills ===

SELECT COUNT(*) AS bseg_rows,
       SUM(CASE WHEN TRIM(bs.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bseg_populated,
       SUM(CASE WHEN TRIM(b.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_header_populated,
       SUM(CASE WHEN TRIM(a.bill_cyc_cd) IS NOT NULL AND TRIM(b.bill_cyc_cd) IS NULL THEN 1 ELSE 0 END) AS acct_only_blank_bill
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_bill b ON b.bill_id = bs.bill_id AND b.bill_stat_flg = 'C '
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id;

PROMPT === Expected post-fix snapshot coverage (simulated COALESCE) ===

SELECT COUNT(*) AS bseg_rows,
       SUM(CASE WHEN COALESCE(b.bill_cyc_cd, a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS expected_bill_bill_cyc,
       SUM(CASE WHEN COALESCE(bs.bill_cyc_cd, b.bill_cyc_cd, a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS expected_bseg_bill_cyc
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_bill b ON b.bill_id = bs.bill_id AND b.bill_stat_flg = 'C '
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id;

PROMPT === Current snapshot: BSEG_BILLED_USAGE_RPT_CURR ===

SELECT COUNT(*) AS snap_rows,
       SUM(CASE WHEN TRIM(bill_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_bill_cyc_populated,
       SUM(CASE WHEN TRIM(bseg_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bseg_bill_cyc_populated
FROM cisadm.bseg_billed_usage_rpt_curr;

PROMPT === Current snapshot: BSEG_SQ_USAGE_RPT_CURR ===

SELECT COUNT(*) AS snap_rows,
       SUM(CASE WHEN TRIM(bill_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_bill_cyc_populated,
       SUM(CASE WHEN TRIM(bseg_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bseg_bill_cyc_populated
FROM cisadm.bseg_sq_usage_rpt_curr;

PROMPT === FT_RPT_CURR (already sources acct.bill_cyc_cd) ===

SELECT COUNT(*) AS snap_rows,
       SUM(CASE WHEN TRIM(bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_cyc_populated
FROM cisadm.ft_rpt_curr;
