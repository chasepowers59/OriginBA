-- 4a) Manual first run (full-history baseline)
BEGIN
    cisadm.refresh_new_service_pipeline_rpt_curr;
END;
/

-- 4b) Row count sanity
SELECT COUNT(*) AS snapshot_count
FROM cisadm.new_service_pipeline_rpt_curr;

SELECT COUNT(*) AS source_pipeline_count
FROM cisadm.ci_sa sa
WHERE NULLIF(TRIM(sa.sa_status_flg), '') IN ('10', '20')
  AND (
      NULLIF(TRIM(sa.prop_sa_stat_flg), '') IS NULL
      OR NULLIF(TRIM(sa.prop_sa_stat_flg), '') IN ('10', '20')
  );

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    sa_id,
    COUNT(*) AS row_count
FROM cisadm.new_service_pipeline_rpt_curr
GROUP BY sa_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage for descriptive fields
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN prop_sa_stat_desc IS NULL AND prop_sa_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_prop_sa_stat_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN svc_type_desc IS NULL AND svc_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_svc_type_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN prem_type_desc IS NULL AND prem_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_prem_type_desc,
    SUM(CASE WHEN state_desc IS NULL AND state IS NOT NULL THEN 1 ELSE 0 END) AS missing_state_desc,
    SUM(CASE WHEN customer_name IS NULL AND per_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN address1 IS NULL AND char_prem_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_address_with_prem_id
FROM cisadm.new_service_pipeline_rpt_curr;

-- 4e) Population profile by SA status
SELECT
    sa_status_flg,
    sa_status_desc,
    COUNT(*) AS sa_count,
    SUM(CASE WHEN stale_pending_sw = 'Y' THEN 1 ELSE 0 END) AS stale_pending_count
FROM cisadm.new_service_pipeline_rpt_curr
GROUP BY
    sa_status_flg,
    sa_status_desc
ORDER BY
    sa_count DESC,
    sa_status_flg;

-- 4f) Population profile by proposal status
SELECT
    prop_sa_stat_flg,
    prop_sa_stat_desc,
    sa_status_flg,
    COUNT(*) AS sa_count
FROM cisadm.new_service_pipeline_rpt_curr
GROUP BY
    prop_sa_stat_flg,
    prop_sa_stat_desc,
    sa_status_flg
ORDER BY
    sa_count DESC,
    prop_sa_stat_flg,
    sa_status_flg;

-- 4g) Recently started active profile
SELECT
    sa_type_cd,
    sa_type_desc,
    COUNT(*) AS recently_started_active_count
FROM cisadm.new_service_pipeline_rpt_curr
WHERE NULLIF(TRIM(sa_status_flg), '') = '20'
  AND start_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
GROUP BY
    sa_type_cd,
    sa_type_desc
ORDER BY
    recently_started_active_count DESC,
    sa_type_cd;

-- 4h) Stale pending parity check against source
SELECT COUNT(*) AS snap_stale_pending_count
FROM cisadm.new_service_pipeline_rpt_curr
WHERE stale_pending_sw = 'Y';

SELECT COUNT(*) AS src_stale_pending_count
FROM cisadm.ci_sa sa
WHERE NULLIF(TRIM(sa.sa_status_flg), '') = '10'
  AND sa.start_dt IS NOT NULL
  AND TRUNC(sa.start_dt) < TRUNC(SYSDATE)
  AND (
      NULLIF(TRIM(sa.prop_sa_stat_flg), '') IS NULL
      OR NULLIF(TRIM(sa.prop_sa_stat_flg), '') IN ('10', '20')
  );

-- 4i) Premise coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN char_prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_char_prem_id,
    SUM(CASE WHEN prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_resolved_prem_id,
    SUM(CASE WHEN address1 IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_address1
FROM cisadm.new_service_pipeline_rpt_curr;

-- 4j) Optional CM_FT_BAL overlay coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_bal_cur_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_ft_bal_cur_amt,
    SUM(CASE WHEN ft_bal_tot_amt IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_ft_bal_tot_amt
FROM cisadm.new_service_pipeline_rpt_curr;

-- 4k) Spot-check pipeline rows
SELECT
    sa_id,
    acct_id,
    sa_status_flg,
    sa_status_desc,
    prop_sa_stat_flg,
    prop_sa_stat_desc,
    enrl_id,
    start_dt,
    end_dt,
    customer_name,
    address1,
    city,
    state,
    stale_pending_sw,
    days_since_created,
    days_until_start
FROM cisadm.new_service_pipeline_rpt_curr
ORDER BY
    CASE WHEN stale_pending_sw = 'Y' THEN 0 ELSE 1 END,
    days_since_created DESC NULLS LAST,
    sa_id
FETCH FIRST 25 ROWS ONLY;
