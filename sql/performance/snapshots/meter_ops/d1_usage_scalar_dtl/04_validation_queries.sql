-- 4a) Manual first run
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_usage_scalar_dtl;

-- 4c) Duplicate natural-key check (should return 0 rows)
SELECT
    d1_usage_id,
    seq_num,
    COUNT(*) AS row_count
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
GROUP BY
    d1_usage_id,
    seq_num
HAVING COUNT(*) > 1;

-- 4d) Quantity reconciliation
SELECT
    SUM(quantity) AS snapshot_quantity,
    SUM(final_quantity) AS snapshot_final_quantity
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

SELECT
    SUM(quantity) AS source_quantity,
    SUM(final_quantity) AS source_final_quantity
FROM cisadm.d1_usage_scalar_dtl;

-- 4e) Coverage and enrichment profile
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN d1_final_uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_final_uom,
    SUM(CASE WHEN sa_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_sa,
    SUM(CASE WHEN acct_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_account,
    SUM(CASE WHEN cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_customer_class,
    SUM(CASE WHEN prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_premise,
    SUM(CASE WHEN bridge_method IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_c1_bridge
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

-- 4f) Description coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN d1_uom_desc IS NULL AND d1_uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_raw_uom_desc,
    SUM(CASE WHEN d1_final_uom_desc IS NULL AND d1_final_uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_final_uom_desc,
    SUM(CASE WHEN d1_usage_desc IS NULL AND d1_usage_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_usage_flag_desc,
    SUM(CASE WHEN measr_comp_usage_desc IS NULL AND measr_comp_usage_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_measr_comp_usage_desc,
    SUM(CASE WHEN msr_peak_qty_desc IS NULL AND msr_peak_qty_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_peak_qty_desc,
    SUM(CASE WHEN msrmt_cond_desc IS NULL AND msrmt_cond_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_msrmt_cond_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_class_desc
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

-- 4g) Consumption profile by final UOM and customer class
SELECT
    cust_cl_cd,
    cust_cl_desc,
    d1_final_uom_cd,
    d1_final_uom_desc,
    COUNT(*) AS scalar_rows,
    SUM(final_quantity) AS total_final_quantity
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
GROUP BY
    cust_cl_cd,
    cust_cl_desc,
    d1_final_uom_cd,
    d1_final_uom_desc
ORDER BY
    total_final_quantity DESC NULLS LAST,
    cust_cl_cd,
    d1_final_uom_cd;

-- 4h) Spot-check sample rows
SELECT *
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
WHERE ROWNUM <= 10;
