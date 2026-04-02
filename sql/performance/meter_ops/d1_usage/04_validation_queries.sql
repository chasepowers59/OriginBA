-- 4a) Manual first run
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
-- Should match exactly
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

-- 4d) Optional-bridge and enrichment coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN us_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_us_id,
    SUM(CASE WHEN us_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_subscription,
    SUM(CASE WHEN is_estimate_flg IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_boda_detail,
    SUM(CASE WHEN bridge_method IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_c1_bridge,
    SUM(CASE WHEN sa_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_sa,
    SUM(CASE WHEN acct_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_account,
    SUM(CASE WHEN customer_name IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_customer
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

-- 4f) D1_USAGE_PERIOD_SQ aggregate reconciliation
SELECT
    SUM(period_sq_row_count) AS snap_period_sq_rows,
    SUM(period_sq_total_quantity) AS snap_period_sq_quantity
FROM cisadm.d1_usage_rpt_curr;

SELECT
    COUNT(*) AS src_period_sq_rows,
    SUM(quantity) AS src_period_sq_quantity
FROM cisadm.d1_usage_period_sq;

-- 4g) D1_USAGE_SCALAR_DTL aggregate reconciliation
SELECT
    SUM(scalar_row_count) AS snap_scalar_rows,
    SUM(scalar_total_quantity) AS snap_scalar_quantity,
    SUM(scalar_total_final_quantity) AS snap_scalar_final_quantity
FROM cisadm.d1_usage_rpt_curr;

SELECT
    COUNT(*) AS src_scalar_rows,
    SUM(quantity) AS src_scalar_quantity,
    SUM(final_quantity) AS src_scalar_final_quantity
FROM cisadm.d1_usage_scalar_dtl;

-- 4h) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bo_status_desc IS NULL AND bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_status_desc,
    SUM(CASE WHEN us_bo_status_desc IS NULL AND us_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_subscription_status_desc,
    SUM(CASE WHEN d1_usg_cal_type_desc IS NULL AND d1_usg_cal_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_calc_type_desc,
    SUM(CASE WHEN d1_spr_desc IS NULL AND d1_spr_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_spr_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN c1_bo_status_desc IS NULL AND c1_bo_status_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_c1_status_desc
FROM cisadm.d1_usage_rpt_curr;

-- 4i) Quantity-family profile from the aggregated header
SELECT
    period_sq_sole_uom_cd,
    period_sq_sole_uom_desc,
    COUNT(*) AS usage_rows,
    SUM(period_sq_total_quantity) AS total_quantity
FROM cisadm.d1_usage_rpt_curr
GROUP BY
    period_sq_sole_uom_cd,
    period_sq_sole_uom_desc
ORDER BY
    usage_rows DESC,
    period_sq_sole_uom_cd;

-- 4j) Spot-check bridged and unbridged samples
SELECT *
FROM cisadm.d1_usage_rpt_curr
WHERE bridge_method IS NOT NULL
  AND ROWNUM <= 10;

SELECT *
FROM cisadm.d1_usage_rpt_curr
WHERE bridge_method IS NULL
  AND ROWNUM <= 10;
