-- Odessa DEV: discover valid CISADM codes before inserting test data.
-- Read-only. Run every time config changes or before a new workstream pack.

PROMPT === 1. Bill cycles (use on CI_ACCT and CI_BILL) ===
SELECT bc.bill_cyc_cd,
       TRIM(bc.bill_cyc_cd) AS bill_cyc_trim,
       bcl.descr
FROM   cisadm.ci_bill_cyc bc
LEFT JOIN cisadm.ci_bill_cyc_l bcl
       ON bcl.bill_cyc_cd = bc.bill_cyc_cd
      AND bcl.language_cd = 'ENG'
ORDER  BY bc.bill_cyc_cd;

PROMPT === 2. Water SA types (billing) ===
SELECT sa_type_cd, cis_division, bill_seg_type_cd
FROM   cisadm.ci_sa_type
WHERE  sa_type_cd LIKE 'W%'
ORDER  BY sa_type_cd;

PROMPT === 3. Status flags (lookup labels) ===
SELECT TRIM(field_name) AS field_name, field_value, descr
FROM   cisadm.ci_lookup_val_l
WHERE  language_cd = 'ENG'
  AND  TRIM(field_name) IN ('BILL_STAT_FLG', 'BSEG_STAT_FLG', 'SA_STATUS_FLG')
ORDER  BY field_name, field_value;

PROMPT === 4. Account segmentation codes (top in use) ===
SELECT cust_cl_cd, COUNT(*) cnt
FROM   cisadm.ci_acct
WHERE  TRIM(cust_cl_cd) IS NOT NULL
GROUP  BY cust_cl_cd
ORDER  BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

SELECT coll_cl_cd, COUNT(*) cnt
FROM   cisadm.ci_acct
WHERE  TRIM(coll_cl_cd) IS NOT NULL
GROUP  BY coll_cl_cd
ORDER  BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

SELECT bud_plan_cd, COUNT(*) cnt
FROM   cisadm.ci_acct
WHERE  TRIM(bud_plan_cd) IS NOT NULL
GROUP  BY bud_plan_cd
ORDER  BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT === 5. CIS division + currency in use ===
SELECT cis_division, currency_cd, COUNT(*) cnt
FROM   cisadm.ci_acct
GROUP  BY cis_division, currency_cd
ORDER  BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT === 6. CI_ACCT_PER relationship + bill route (sample) ===
SELECT acct_rel_type_cd, bill_addr_srce_flg, bill_rte_type_cd, bill_format_flg,
       COUNT(*) cnt
FROM   cisadm.ci_acct_per
GROUP  BY acct_rel_type_cd, bill_addr_srce_flg, bill_rte_type_cd, bill_format_flg
ORDER  BY cnt DESC
FETCH FIRST 10 ROWS ONLY;

PROMPT === 7. Bill vs account bill cycle gap (Odessa conversion check) ===
SELECT COUNT(*) AS total_bills,
       COUNT(CASE WHEN TRIM(bill.bill_cyc_cd) IS NOT NULL THEN 1 END) AS bills_with_cyc,
       COUNT(CASE WHEN TRIM(acct.bill_cyc_cd) IS NOT NULL THEN 1 END) AS accts_with_cyc
FROM   cisadm.ci_bill bill
JOIN   cisadm.ci_acct acct ON acct.acct_id = bill.acct_id;

PROMPT === 8. Golden template candidates (completed water + calc + SQ) ===
SELECT bill.acct_id,
       bill.bill_id,
       bseg.bseg_id,
       sa.sa_type_cd,
       TRIM(bill.bill_cyc_cd) AS bill_cyc,
       TRIM(acct.bill_cyc_cd) AS acct_cyc,
       bill.bill_stat_flg,
       bseg.bseg_stat_flg,
       calc.rs_cd,
       sq.sqi_cd,
       sq.uom_cd,
       sq.bill_sq
FROM   cisadm.ci_bill bill
JOIN   cisadm.ci_acct acct ON acct.acct_id = bill.acct_id
JOIN   cisadm.ci_bseg bseg ON bseg.bill_id = bill.bill_id
JOIN   cisadm.ci_sa sa ON sa.sa_id = bseg.sa_id
JOIN   cisadm.ci_bseg_calc calc ON calc.bseg_id = bseg.bseg_id
JOIN   cisadm.ci_bseg_sq sq ON sq.bseg_id = bseg.bseg_id
WHERE  bill.bill_stat_flg = 'C '
  AND  bseg.bseg_stat_flg = '50'
  AND  sa.sa_type_cd LIKE 'W-%'
  AND  ROWNUM <= 20
ORDER  BY bill.complete_dttm DESC NULLS LAST;

PROMPT === 9. NOT NULL columns on core tables (sanity) ===
SELECT table_name, column_name
FROM   all_tab_columns
WHERE  owner = 'CISADM'
  AND  table_name IN (
         'CI_PER', 'CI_PER_NAME', 'CI_ACCT', 'CI_ACCT_PER',
         'CI_PREM', 'CI_SP', 'CI_SA', 'CI_SA_SP',
         'CI_BILL', 'CI_BSEG', 'CI_BSEG_CALC', 'CI_BSEG_SQ'
       )
  AND  nullable = 'N'
ORDER  BY table_name, column_id;

PROMPT === 10. Todo types in use (for workflow pack) ===
SELECT td_type_cd, entry_status_flg, COUNT(*) cnt
FROM   cisadm.ci_td_entry
GROUP  BY td_type_cd, entry_status_flg
ORDER  BY cnt DESC
FETCH FIRST 15 ROWS ONLY;

PROMPT === 11. Install event statuses (meter install On/Off) ===
SELECT bo_status_cd, descr
FROM   cisadm.f1_bus_obj_status_l
WHERE  bus_obj_cd = 'D1-InstallEvent'
  AND  language_cd = 'ENG'
ORDER  BY bo_status_cd;

SELECT field_value, descr
FROM   cisadm.ci_lookup_val_l
WHERE  language_cd = 'ENG'
  AND  TRIM(field_name) = 'ARM_STAT_FLG'
ORDER  BY field_value;

PROMPT === 12. Sample install events by status ===
SELECT ie.install_evt_id,
       ie.bo_status_cd,
       st.descr AS status_desc,
       ie.d1_install_dttm,
       ie.d1_removal_dttm,
       ie.d1_sp_id,
       ie.device_config_id
FROM   cisadm.d1_install_evt ie
LEFT JOIN cisadm.f1_bus_obj_status_l st
       ON st.bus_obj_cd = 'D1-InstallEvent'
      AND st.bo_status_cd = ie.bo_status_cd
      AND st.language_cd = 'ENG'
WHERE  ROWNUM <= 20
ORDER  BY ie.status_upd_dttm DESC NULLS LAST;
