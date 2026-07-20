-- Odessa DEV test data manifest (READ-ONLY).
-- Run before any pack load to confirm template still exists and ODEV IDs are free.

PROMPT === ODEV collision check (must all be 0 before load) ===
SELECT 'CI_PER' AS entity, COUNT(*) AS collisions
FROM   cisadm.ci_per WHERE per_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_ACCT', COUNT(*) FROM cisadm.ci_acct WHERE acct_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_PREM', COUNT(*) FROM cisadm.ci_prem WHERE prem_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_SA', COUNT(*) FROM cisadm.ci_sa WHERE sa_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_SP', COUNT(*) FROM cisadm.ci_sp WHERE sp_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_BILL', COUNT(*) FROM cisadm.ci_bill WHERE bill_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_BSEG', COUNT(*) FROM cisadm.ci_bseg WHERE bseg_id LIKE 'ODEV%';

PROMPT === Pack B01 golden template (must return rows) ===
SELECT 'template_acct' AS label, a.acct_id AS id, pn.entity_name
FROM   cisadm.ci_acct a
JOIN   cisadm.ci_acct_per ap ON ap.acct_id = a.acct_id AND ap.main_cust_sw = 'Y'
JOIN   cisadm.ci_per_name pn ON pn.per_id = ap.per_id AND pn.prim_name_sw = 'Y'
WHERE  a.acct_id = '1110100087';

SELECT 'template_sa' AS label, sa_id AS id, sa_type_cd, sa_status_flg, char_prem_id
FROM   cisadm.ci_sa WHERE sa_id = '7790352119';

SELECT 'template_bill' AS label, bill_id AS id, bill_stat_flg, TRIM(bill_cyc_cd) AS bill_cyc, bill_dt
FROM   cisadm.ci_bill WHERE bill_id = '856601546942';

SELECT 'template_bseg_water' AS label, bs.bseg_id AS id, sa.sa_type_cd, calc.calc_amt, sq.sqi_cd, sq.uom_cd, sq.bill_sq
FROM   cisadm.ci_bseg bs
JOIN   cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
JOIN   cisadm.ci_bseg_calc calc ON calc.bseg_id = bs.bseg_id
LEFT JOIN cisadm.ci_bseg_sq sq ON sq.bseg_id = bs.bseg_id
WHERE  bs.bseg_id = '776805100203';

PROMPT === Config constants for pack B01 (from 2026-06 discovery) ===
SELECT 'bill_cyc_cd' AS config_key, '83' AS use_value, 'From template acct; also valid: 75,95,41,...' AS note FROM dual
UNION ALL SELECT 'cis_division', 'DIV1', 'All water SA types' FROM dual
UNION ALL SELECT 'currency_cd', 'USD', 'CI_ACCT / CI_SA' FROM dual
UNION ALL SELECT 'cust_cl_cd', 'R', 'Residential' FROM dual
UNION ALL SELECT 'coll_cl_cd', 'RES', 'Residential collection class' FROM dual
UNION ALL SELECT 'sa_type_cd', 'W-RES', 'Water residential' FROM dual
UNION ALL SELECT 'sa_status_flg', '20', 'Active' FROM dual
UNION ALL SELECT 'bill_stat_flg', 'C ', 'Complete (2-char, trailing space)' FROM dual
UNION ALL SELECT 'bseg_stat_flg', '50', 'Frozen' FROM dual
UNION ALL SELECT 'acct_rel_type_cd', 'MAIN', 'CI_ACCT_PER' FROM dual
UNION ALL SELECT 'bill_addr_srce_flg', 'PREM', 'Most common on Odessa' FROM dual
UNION ALL SELECT 'bill_rte_type_cd', 'POSTAL', 'Most common' FROM dual
UNION ALL SELECT 'bill_format_flg', 'D', 'Most common' FROM dual
UNION ALL SELECT 'sq_pattern', 'DAYS+GAL bill_sq=1', 'Odessa water billing pattern' FROM dual;
