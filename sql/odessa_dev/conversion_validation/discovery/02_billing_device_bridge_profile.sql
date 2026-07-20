-- Discovery: billing + device bridge profile (informational).

PROMPT === Bill cycle: acct populated vs bill header blank ===

SELECT COUNT(*) AS bills_with_acct_cycle,
       SUM(CASE WHEN TRIM(b.bill_cyc_cd) IS NULL THEN 1 ELSE 0 END) AS bill_header_blank,
       SUM(CASE WHEN TRIM(b.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS bill_header_populated
FROM cisadm.ci_bill b
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id
WHERE TRIM(a.bill_cyc_cd) IS NOT NULL;

PROMPT === D1EI identifier coverage on manual meter installs ===

SELECT COUNT(*) AS active_install_cnt,
       SUM(CASE WHEN spid.d1_sp_id IS NOT NULL THEN 1 ELSE 0 END) AS with_d1ei,
       SUM(CASE WHEN spid.d1_sp_id IS NULL THEN 1 ELSE 0 END) AS missing_d1ei
FROM cisadm.d1_install_evt ie
LEFT JOIN cisadm.d1_sp_identifier spid
       ON spid.d1_sp_id = ie.d1_sp_id
      AND spid.sp_id_type_flg = 'D1EI'
WHERE ie.bus_obj_cd = 'D1-ManualMeterInstallEvent'
  AND ie.d1_removal_dttm IS NULL
  AND ie.bo_status_cd = 'ON';

PROMPT === Water BSEG SQ pattern (DAYS + GAL + bill_sq=1) ===

SELECT COUNT(*) AS sq_rows,
       SUM(CASE WHEN sq.sqi_cd = 'DAYS' AND sq.uom_cd = 'GAL' AND sq.bill_sq = 1 THEN 1 ELSE 0 END) AS days_gal_one
FROM cisadm.ci_bseg_sq sq
JOIN cisadm.ci_bseg bs ON bs.bseg_id = sq.bseg_id
JOIN cisadm.ci_sa sa ON sa.sa_id = bs.sa_id
WHERE sa.sa_type_cd LIKE 'W-%';
