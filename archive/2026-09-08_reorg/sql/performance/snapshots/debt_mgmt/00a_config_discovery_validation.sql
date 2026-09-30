-- Debt Management Config Discovery / Validation
-- Purpose:
--   Read-only discovery pack to determine which debt-management objects are
--   actually active and populated in the current tenant before building
--   snapshot tables.
--
-- Recommended interpretation:
--   1) If CI_FT arrears population is healthy, build ACCT_DEBT_RPT_CURR first.
--   2) If CI_COLL_PROC is populated, build COLL_PROC_RPT_CURR next.
--   3) If C1_PA_RQST is populated, build PA_RQST_RPT_CURR next.
--   4) If C1_BI_WOPROC_VW or CI_WO_PROC is populated, build WO_PROC_RPT_CURR.
--   5) Only model agency or severance after proving they are active and useful.

--------------------------------------------------------------------------------
-- 1) Base debt truth from CI_FT
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS ft_rows,
    COUNT(CASE WHEN ft.freeze_sw = 'Y' THEN 1 END) AS frozen_ft_rows,
    COUNT(CASE WHEN ft.freeze_sw = 'Y'
                 AND ft.not_in_ars_sw = 'N'
                 AND ft.ft_type_flg NOT IN ('PS', 'PX')
                 AND ft.ars_dt IS NOT NULL
               THEN 1 END) AS governed_arrears_ft_rows,
    COUNT(DISTINCT CASE WHEN ft.freeze_sw = 'Y'
                          AND ft.not_in_ars_sw = 'N'
                          AND ft.ft_type_flg NOT IN ('PS', 'PX')
                          AND ft.ars_dt IS NOT NULL
                        THEN ft.sa_id END) AS governed_arrears_sa_count,
    MIN(ft.ars_dt) AS min_ars_dt,
    MAX(ft.ars_dt) AS max_ars_dt
FROM cisadm.ci_ft ft;

--------------------------------------------------------------------------------
-- 2) Account-level debt candidate population
--------------------------------------------------------------------------------
SELECT
    COUNT(DISTINCT acct.acct_id) AS account_count,
    COUNT(DISTINCT sa.sa_id) AS sa_count,
    SUM(ft.cur_amt) AS total_debt,
    SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt <= 30 THEN ft.cur_amt ELSE 0 END) AS debt_0_30,
    SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt BETWEEN 31 AND 60 THEN ft.cur_amt ELSE 0 END) AS debt_31_60,
    SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt > 60 THEN ft.cur_amt ELSE 0 END) AS debt_over_60
FROM cisadm.ci_acct acct
JOIN cisadm.ci_sa sa
  ON sa.acct_id = acct.acct_id
 AND NULLIF(TRIM(sa.sa_status_flg), '') = '20'
JOIN cisadm.ci_ft ft
  ON ft.sa_id = sa.sa_id
 AND ft.freeze_sw = 'Y'
 AND ft.not_in_ars_sw = 'N'
 AND ft.ft_type_flg NOT IN ('PS', 'PX')
 AND ft.ars_dt IS NOT NULL;

--------------------------------------------------------------------------------
-- 3) Collection class / credit review coverage
--------------------------------------------------------------------------------
SELECT
    NULLIF(TRIM(acct.coll_cl_cd), '') AS coll_cl_cd,
    COUNT(*) AS account_count,
    COUNT(CASE WHEN acct.cr_review_dt IS NOT NULL THEN 1 END) AS with_credit_review_dt
FROM cisadm.ci_acct acct
GROUP BY NULLIF(TRIM(acct.coll_cl_cd), '')
ORDER BY account_count DESC, coll_cl_cd;

--------------------------------------------------------------------------------
-- 4) Collection process presence and recent activity
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS coll_proc_rows,
    COUNT(DISTINCT coll_proc_id) AS distinct_coll_proc_id,
    COUNT(DISTINCT acct_id) AS distinct_acct_id,
    MIN(cre_dttm) AS min_cre_dttm,
    MAX(cre_dttm) AS max_cre_dttm,
    SUM(ars_amt) AS total_coll_proc_ars_amt
FROM cisadm.ci_coll_proc;

SELECT
    NULLIF(TRIM(cp.coll_status_flg), '') AS coll_status_flg,
    NULLIF(TRIM(cp.coll_proc_tmpl_cd), '') AS coll_proc_tmpl_cd,
    COUNT(*) AS row_count,
    COUNT(DISTINCT cp.acct_id) AS acct_count,
    SUM(cp.ars_amt) AS total_ars_amt
FROM cisadm.ci_coll_proc cp
WHERE cp.cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -12)
GROUP BY
    NULLIF(TRIM(cp.coll_status_flg), ''),
    NULLIF(TRIM(cp.coll_proc_tmpl_cd), '')
ORDER BY row_count DESC, coll_status_flg, coll_proc_tmpl_cd;

--------------------------------------------------------------------------------
-- 5) Collection process SA linkage density
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS coll_proc_sa_rows,
    COUNT(DISTINCT coll_proc_id) AS coll_proc_count,
    COUNT(DISTINCT sa_id) AS sa_count,
    SUM(ars_amt) AS total_ars_amt
FROM cisadm.ci_coll_proc_sa;

SELECT
    COUNT(*) AS coll_proc_without_sa_links
FROM cisadm.ci_coll_proc cp
LEFT JOIN cisadm.ci_coll_proc_sa cps
  ON cps.coll_proc_id = cp.coll_proc_id
WHERE cps.coll_proc_id IS NULL;

--------------------------------------------------------------------------------
-- 6) Payment arrangement request presence and related-object usage
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS pa_rqst_rows,
    COUNT(DISTINCT pa_rqst_id) AS distinct_pa_rqst_id,
    COUNT(DISTINCT acct_id) AS distinct_acct_id,
    MIN(cre_dttm) AS min_cre_dttm,
    MAX(cre_dttm) AS max_cre_dttm,
    SUM(pa_rqst_tot_amt) AS total_request_amount
FROM cisadm.c1_pa_rqst;

SELECT
    NULLIF(TRIM(pa.bo_status_cd), '') AS bo_status_cd,
    NULLIF(TRIM(pa.pa_rqst_type_cd), '') AS pa_rqst_type_cd,
    NULLIF(TRIM(pa.pa_rqst_rslt_flg), '') AS pa_rqst_rslt_flg,
    COUNT(*) AS row_count,
    SUM(pa.pa_rqst_tot_amt) AS total_request_amount
FROM cisadm.c1_pa_rqst pa
WHERE pa.cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -12)
GROUP BY
    NULLIF(TRIM(pa.bo_status_cd), ''),
    NULLIF(TRIM(pa.pa_rqst_type_cd), ''),
    NULLIF(TRIM(pa.pa_rqst_rslt_flg), '')
ORDER BY row_count DESC, bo_status_cd, pa_rqst_type_cd;

SELECT
    NULLIF(TRIM(pro.pa_rqst_rel_obj_type_flg), '') AS pa_rqst_rel_obj_type_flg,
    NULLIF(TRIM(pro.maint_obj_cd), '') AS maint_obj_cd,
    COUNT(*) AS row_count
FROM cisadm.c1_pa_rqst_rel_obj pro
GROUP BY
    NULLIF(TRIM(pro.pa_rqst_rel_obj_type_flg), ''),
    NULLIF(TRIM(pro.maint_obj_cd), '')
ORDER BY row_count DESC, pa_rqst_rel_obj_type_flg, maint_obj_cd;

--------------------------------------------------------------------------------
-- 7) Write-off process presence: raw tables
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS wo_proc_rows,
    COUNT(DISTINCT wo_proc_id) AS distinct_wo_proc_id,
    COUNT(DISTINCT acct_id) AS distinct_acct_id,
    MIN(cre_dttm) AS min_cre_dttm,
    MAX(cre_dttm) AS max_cre_dttm
FROM cisadm.ci_wo_proc;

SELECT
    NULLIF(TRIM(wp.wo_status_flg), '') AS wo_status_flg,
    NULLIF(TRIM(wp.wo_proc_tmpl_cd), '') AS wo_proc_tmpl_cd,
    COUNT(*) AS row_count,
    COUNT(DISTINCT wp.acct_id) AS acct_count
FROM cisadm.ci_wo_proc wp
WHERE wp.cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -12)
GROUP BY
    NULLIF(TRIM(wp.wo_status_flg), ''),
    NULLIF(TRIM(wp.wo_proc_tmpl_cd), '')
ORDER BY row_count DESC, wo_status_flg, wo_proc_tmpl_cd;

SELECT
    COUNT(*) AS wo_proc_sa_rows,
    COUNT(DISTINCT wo_proc_id) AS wo_proc_count,
    COUNT(DISTINCT sa_id) AS sa_count,
    SUM(ars_amt) AS total_ars_amt
FROM cisadm.ci_wo_proc_sa;

--------------------------------------------------------------------------------
-- 8) Write-off BI view presence
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS woproc_view_rows,
    COUNT(DISTINCT uncoll_proc_id) AS distinct_uncoll_proc_id,
    COUNT(DISTINCT acct_id) AS distinct_acct_id,
    MIN(cre_dttm) AS min_cre_dttm,
    MAX(cre_dttm) AS max_cre_dttm,
    SUM(ars_at_start) AS total_ars_at_start,
    SUM(ars_at_end) AS total_ars_at_end
FROM cisadm.c1_bi_woproc_vw;

--------------------------------------------------------------------------------
-- 9) Collection agency reference presence
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS coll_agy_ref_rows,
    COUNT(DISTINCT wo_proc_id) AS wo_proc_count
FROM cisadm.ci_coll_agy_ref;

--------------------------------------------------------------------------------
-- 10) Severance / disconnection discovery in Oracle metadata
--     If this returns useful populated objects, severance may deserve its own
--     process snapshot later. If it returns nothing meaningful, do not force it
--     into the first debt-management snapshot wave.
--------------------------------------------------------------------------------
SELECT
    owner,
    object_type,
    object_name
FROM (
    SELECT owner, 'TABLE' AS object_type, table_name AS object_name
    FROM all_tables
    WHERE owner = 'CISADM'
      AND (
            UPPER(table_name) LIKE '%SEVER%'
         OR UPPER(table_name) LIKE '%DISC%'
         OR UPPER(table_name) LIKE '%CUT%'
      )
    UNION ALL
    SELECT owner, 'VIEW' AS object_type, view_name AS object_name
    FROM all_views
    WHERE owner = 'CISADM'
      AND (
            UPPER(view_name) LIKE '%SEVER%'
         OR UPPER(view_name) LIKE '%DISC%'
         OR UPPER(view_name) LIKE '%CUT%'
      )
)
ORDER BY object_type, object_name;

--------------------------------------------------------------------------------
-- 11) Recent date recency summary across key process tables
--------------------------------------------------------------------------------
SELECT 'CI_COLL_PROC' AS object_name, MAX(cre_dttm) AS max_activity_dttm FROM cisadm.ci_coll_proc
UNION ALL
SELECT 'C1_PA_RQST', MAX(cre_dttm) FROM cisadm.c1_pa_rqst
UNION ALL
SELECT 'CI_WO_PROC', MAX(cre_dttm) FROM cisadm.ci_wo_proc
UNION ALL
SELECT 'C1_BI_WOPROC_VW', MAX(cre_dttm) FROM cisadm.c1_bi_woproc_vw
ORDER BY 1;
