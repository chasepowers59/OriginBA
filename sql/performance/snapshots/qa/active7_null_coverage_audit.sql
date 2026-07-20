-- Active 7 snapshot null-coverage audit (read-only).
-- Run on CityCorp for reference and Odessa DEV for target validation.

SELECT 'FT_RPT_CURR' AS snapshot_name,
       COUNT(*) AS row_count,
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END) AS has_key_1,
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END) AS has_key_2,
       SUM(CASE WHEN TRIM(bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS has_cycle
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(bill_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(bill_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(c1_bill_cyc_cd) IS NOT NULL OR TRIM(bseg_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(acct_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(sa_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(c1_bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL
SELECT 'D1_MSRMT_RPT_CURR',
       COUNT(*),
       SUM(CASE WHEN TRIM(measr_comp_id) IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN msrmt_dttm IS NOT NULL THEN 1 ELSE 0 END),
       SUM(CASE WHEN TRIM(msrmt_bus_obj_cd) IS NOT NULL THEN 1 ELSE 0 END)
FROM cisadm.d1_msrmt_rpt_curr;

PROMPT === Source expectation: billed-usage bill cycles (post-fix target) ===

SELECT COUNT(*) AS bseg_rows,
       SUM(CASE WHEN COALESCE(b.bill_cyc_cd, a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS expected_bill_bill_cyc,
       SUM(CASE WHEN COALESCE(bs.bill_cyc_cd, b.bill_cyc_cd, a.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS expected_bseg_bill_cyc
FROM cisadm.ci_bseg bs
JOIN cisadm.ci_bill b ON b.bill_id = bs.bill_id AND b.bill_stat_flg = 'C '
JOIN cisadm.ci_acct a ON a.acct_id = b.acct_id;

PROMPT === Source expectation: FT_GL bseg cycle (post-fix target) ===

SELECT COUNT(*) AS ft_gl_rows,
       SUM(CASE WHEN ft.ft_type_flg IN ('BS','BX') THEN 1 ELSE 0 END) AS bill_seg_ft_rows,
       SUM(CASE WHEN ft.ft_type_flg IN ('BS','BX') AND COALESCE(bseg.bill_cyc_cd, acct.bill_cyc_cd) IS NOT NULL THEN 1 ELSE 0 END) AS expected_bseg_bill_cyc
FROM cisadm.ci_ft_gl gl
JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id AND ft.redundant_sw = 'N'
LEFT JOIN cisadm.ci_bseg bseg ON bseg.bseg_id = ft.sibling_id AND bseg.bill_id = ft.bill_id AND ft.ft_type_flg IN ('BS','BX')
LEFT JOIN cisadm.ci_sa sa ON sa.sa_id = ft.sa_id
LEFT JOIN cisadm.ci_acct acct ON acct.acct_id = sa.acct_id;
