-- Odessa DEV: remove ALL synthetic rows with ODEV-* keys.
-- Run only when intentionally cleaning test packs. Review counts first.
-- NOT executed automatically.

PROMPT === Rows to be deleted (preview) ===
SELECT 'CI_BSEG_SQ' AS tbl, COUNT(*) AS cnt
FROM   cisadm.ci_bseg_sq sq
WHERE  EXISTS (SELECT 1 FROM cisadm.ci_bseg bs WHERE bs.bseg_id = sq.bseg_id AND bs.bseg_id LIKE 'ODEV%')
UNION ALL
SELECT 'CI_BSEG_CALC', COUNT(*) FROM cisadm.ci_bseg_calc c
WHERE  c.bseg_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_BSEG_EXCP', COUNT(*) FROM cisadm.ci_bseg_excp e
WHERE  e.bseg_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_BSEG', COUNT(*) FROM cisadm.ci_bseg WHERE bseg_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_FT', COUNT(*) FROM cisadm.ci_ft WHERE bill_id LIKE 'ODEV%' OR ft_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_BILL', COUNT(*) FROM cisadm.ci_bill WHERE bill_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_SA_SP', COUNT(*) FROM cisadm.ci_sa_sp WHERE sa_id LIKE 'ODEV%' OR sp_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_SP', COUNT(*) FROM cisadm.ci_sp WHERE sp_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_SA', COUNT(*) FROM cisadm.ci_sa WHERE sa_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_ACCT_PER', COUNT(*) FROM cisadm.ci_acct_per WHERE acct_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_ACCT', COUNT(*) FROM cisadm.ci_acct WHERE acct_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_PER_NAME', COUNT(*) FROM cisadm.ci_per_name WHERE per_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_PER', COUNT(*) FROM cisadm.ci_per WHERE per_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_PREM', COUNT(*) FROM cisadm.ci_prem WHERE prem_id LIKE 'ODEV%'
UNION ALL
SELECT 'CI_TD_ENTRY', COUNT(*) FROM cisadm.ci_td_entry WHERE td_entry_id LIKE 'ODEV%'
UNION ALL
SELECT 'D1_INSTALL_EVT', COUNT(*) FROM cisadm.d1_install_evt WHERE install_evt_id LIKE 'ODEV%'
UNION ALL
SELECT 'D1_MEASR_COMP', COUNT(*) FROM cisadm.d1_measr_comp WHERE measr_comp_id LIKE 'ODEV%'
UNION ALL
SELECT 'D1_DVC_CFG', COUNT(*) FROM cisadm.d1_dvc_cfg WHERE device_config_id LIKE 'ODEV%'
UNION ALL
SELECT 'D1_DVC', COUNT(*) FROM cisadm.d1_dvc WHERE d1_device_id LIKE 'ODEV%'
UNION ALL
SELECT 'D1_SP', COUNT(*) FROM cisadm.d1_sp WHERE d1_sp_id LIKE 'ODEV%';

-- Uncomment block below to execute delete (children first).
/*
DELETE FROM cisadm.ci_bseg_sq sq
 WHERE EXISTS (SELECT 1 FROM cisadm.ci_bseg bs WHERE bs.bseg_id = sq.bseg_id AND bs.bseg_id LIKE 'ODEV%');
DELETE FROM cisadm.ci_bseg_calc_ln WHERE bseg_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_bseg_calc WHERE bseg_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_bseg_excp WHERE bseg_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_bseg_read WHERE bseg_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_ft WHERE bill_id LIKE 'ODEV%' OR ft_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_bseg WHERE bseg_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_bill WHERE bill_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_sa_sp WHERE sa_id LIKE 'ODEV%' OR sp_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_sa_char WHERE sa_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_sp WHERE sp_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_sa WHERE sa_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_acct_per WHERE acct_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_acct WHERE acct_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_per_name WHERE per_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_per WHERE per_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_prem WHERE prem_id LIKE 'ODEV%';
DELETE FROM cisadm.ci_td_entry WHERE td_entry_id LIKE 'ODEV%';
DELETE FROM cisadm.d1_install_evt WHERE install_evt_id LIKE 'ODEV%';
DELETE FROM cisadm.d1_measr_comp WHERE measr_comp_id LIKE 'ODEV%';
DELETE FROM cisadm.d1_dvc_cfg WHERE device_config_id LIKE 'ODEV%';
DELETE FROM cisadm.d1_dvc WHERE d1_device_id LIKE 'ODEV%';
DELETE FROM cisadm.d1_sp WHERE d1_sp_id LIKE 'ODEV%';
COMMIT;
*/
