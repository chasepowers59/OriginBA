-- 4a) Manual first run
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.d1_usage_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_usage;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    d1_usage_id,
    COUNT(*) AS row_count
FROM cisadm.d1_usage_rpt_curr
GROUP BY
    d1_usage_id
HAVING COUNT(*) > 1;

-- 4d) Optional bridge and enrichment coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN us_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_us_id,
    SUM(CASE WHEN us_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_subscription,
    SUM(CASE WHEN bridge_method IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_c1_bridge,
    SUM(CASE WHEN sa_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_sa,
    SUM(CASE WHEN acct_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_account,
    SUM(CASE WHEN cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_customer_class,
    SUM(CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_customer,
    SUM(CASE WHEN prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_premise
FROM cisadm.d1_usage_rpt_curr;

-- 4e) Bridge-method distribution and multiple-match profile
SELECT
    NVL(bridge_method, 'NO_C1_MATCH') AS bridge_method,
    COUNT(*) AS row_count,
    SUM(CASE WHEN NVL(c1_match_count, 0) > 1 THEN 1 ELSE 0 END) AS rows_with_multiple_c1_candidates
FROM cisadm.d1_usage_rpt_curr
GROUP BY
    NVL(bridge_method, 'NO_C1_MATCH')
ORDER BY
    row_count DESC,
    bridge_method;

-- 4f) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_status_desc,
    SUM(CASE WHEN us_bo_status_desc IS NULL AND us_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_subscription_status_desc,
    SUM(CASE WHEN d1_usg_cal_type_desc IS NULL AND d1_usg_cal_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_calc_type_desc,
    SUM(CASE WHEN d1_spr_desc IS NULL AND d1_spr_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_spr_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_class_desc,
    SUM(CASE WHEN c1_bo_status_desc IS NULL AND c1_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_c1_status_desc
FROM cisadm.d1_usage_rpt_curr;

-- 4g) Customer class and service type activity rollup smoke test
SELECT
    cust_cl_cd,
    cust_cl_desc,
    sa_type_cd,
    sa_type_desc,
    COUNT(*) AS usage_rows
FROM cisadm.d1_usage_rpt_curr
GROUP BY
    cust_cl_cd,
    cust_cl_desc,
    sa_type_cd,
    sa_type_desc
ORDER BY
    usage_rows DESC,
    cust_cl_cd,
    sa_type_cd;

-- 4h) Spot-check bridged and unbridged samples
SELECT *
FROM cisadm.d1_usage_rpt_curr
WHERE bridge_method IS NOT NULL
  AND ROWNUM <= 10;

SELECT *
FROM cisadm.d1_usage_rpt_curr
WHERE bridge_method IS NULL
  AND ROWNUM <= 10;
