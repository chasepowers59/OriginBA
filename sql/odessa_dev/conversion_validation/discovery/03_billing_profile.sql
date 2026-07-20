-- Discovery: billing chain profile (informational).

PROMPT === Billing: bill / bseg / sq / ft counts ===

SELECT 'CI_BILL' AS entity, COUNT(*) AS cnt FROM cisadm.ci_bill
UNION ALL SELECT 'CI_BSEG', COUNT(*) FROM cisadm.ci_bseg
UNION ALL SELECT 'CI_BSEG_SQ', COUNT(*) FROM cisadm.ci_bseg_sq
UNION ALL SELECT 'CI_FT', COUNT(*) FROM cisadm.ci_ft
UNION ALL SELECT 'CI_BSEG_EXCP', COUNT(*) FROM cisadm.ci_bseg_excp;

PROMPT === Billing: complete bills with blank header cycle ===

SELECT COUNT(*) AS complete_bills,
       SUM(CASE WHEN TRIM(b.bill_cyc_cd) IS NULL AND TRIM(a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS blank_header_with_acct_cycle
FROM cisadm.ci_bill b
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id
WHERE b.bill_stat_flg = 'C ';

PROMPT === Billing: frozen water bseg without SQ ===

SELECT COUNT(*) AS frozen_water_bseg,
       SUM(CASE WHEN sq.bseg_id IS NULL THEN 1 ELSE 0 END) AS without_sq
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
LEFT JOIN cisadm.ci_bseg_sq sq ON sq.bseg_id = bs.bseg_id
WHERE bs.bseg_stat_flg = '50'
  AND sa.sa_type_cd LIKE 'W-%';
