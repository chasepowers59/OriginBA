-- 4a) Manual first run
BEGIN
    cisadm.refresh_d1_msrmt_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
-- Should match exactly
SELECT COUNT(*) AS snapshot_count
FROM cisadm.d1_msrmt_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.d1_msrmt;

-- 4c) Duplicate natural-key check (should return 0 rows)
SELECT
    measr_comp_id,
    msrmt_dttm,
    COUNT(*) AS row_count
FROM cisadm.d1_msrmt_rpt_curr
GROUP BY
    measr_comp_id,
    msrmt_dttm
HAVING COUNT(*) > 1;

-- 4d) Null coverage check (verify joins are resolving descriptions)
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN msrmt_bo_status_desc IS NULL THEN 1 ELSE 0 END) AS missing_msrmt_status_desc,
    SUM(CASE WHEN msrmt_cond_desc IS NULL THEN 1 ELSE 0 END) AS missing_msrmt_cond_desc,
    SUM(CASE WHEN msrmt_use_desc IS NULL THEN 1 ELSE 0 END) AS missing_msrmt_use_desc,
    SUM(CASE WHEN measr_comp_type_desc IS NULL THEN 1 ELSE 0 END) AS missing_mc_type_desc,
    SUM(CASE WHEN d1_sp_type_desc IS NULL THEN 1 ELSE 0 END) AS missing_sp_type_desc,
    SUM(CASE WHEN data_src_desc IS NULL AND init_msrmt_data_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_imd_data_src_desc,
    SUM(CASE WHEN mc_user_name IS NULL AND mc_user_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_mc_user_name
FROM cisadm.d1_msrmt_rpt_curr;

-- 4e) Measurement value reconciliation (snapshot totals must match source)
SELECT
    SUM(msrmt_val) AS snap_msrmt_val,
    SUM(reading_val) AS snap_reading_val
FROM cisadm.d1_msrmt_rpt_curr;

SELECT
    SUM(msrmt_val) AS src_msrmt_val,
    SUM(reading_val) AS src_reading_val
FROM cisadm.d1_msrmt;

-- 4f) Type distribution check (verify all measurement-use values are represented)
SELECT
    msrmt_use_flg,
    msrmt_use_desc,
    COUNT(*) AS row_count
FROM cisadm.d1_msrmt_rpt_curr
GROUP BY
    msrmt_use_flg,
    msrmt_use_desc
ORDER BY
    msrmt_use_flg;

-- 4g) Spot check a sample row end-to-end
SELECT *
FROM cisadm.d1_msrmt_rpt_curr
WHERE orig_init_msrmt_id IS NOT NULL
  AND ROWNUM <= 5;
