-- 4a) Manual first run
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source distinct determinant keys)
-- Should match exactly
SELECT COUNT(*) AS snapshot_count
FROM cisadm.bseg_sq_usage_rpt_curr;

SELECT COUNT(*) AS source_count
FROM (
    SELECT
        sq.bseg_id,
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id,
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
);

-- 4c) Duplicate determinant key check (should return 0 rows)
SELECT
    bseg_id,
    NVL(uom_cd, '~') AS uom_cd_key,
    NVL(tou_cd, '~') AS tou_cd_key,
    NVL(sqi_cd, '~') AS sqi_cd_key,
    COUNT(*) AS row_count
FROM cisadm.bseg_sq_usage_rpt_curr
GROUP BY
    bseg_id,
    NVL(uom_cd, '~'),
    NVL(tou_cd, '~'),
    NVL(sqi_cd, '~')
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN bill_stat_desc IS NULL AND bill_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_status_desc,
    SUM(CASE WHEN bseg_stat_desc IS NULL AND bseg_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN customer_name IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN bill_bill_cyc_desc IS NULL AND bill_bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_bill_cyc_desc,
    SUM(CASE WHEN bseg_bill_cyc_desc IS NULL AND bseg_bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bseg_bill_cyc_desc,
    SUM(CASE WHEN uom_desc IS NULL AND uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_uom_desc,
    SUM(CASE WHEN tou_desc IS NULL AND tou_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_tou_desc,
    SUM(CASE WHEN sqi_desc IS NULL AND sqi_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sqi_desc
FROM cisadm.bseg_sq_usage_rpt_curr;

-- 4e) Quantity reconciliation
SELECT
    SUM(total_bill_sq) AS snap_total_bill_sq,
    SUM(total_init_sq) AS snap_total_init_sq,
    SUM(sq_line_count) AS snap_sq_line_count
FROM cisadm.bseg_sq_usage_rpt_curr;

SELECT
    SUM(sq.bill_sq) AS src_total_bill_sq,
    SUM(sq.init_sq) AS src_total_init_sq,
    COUNT(*) AS src_sq_line_count
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

-- 4f) Service type by unit profile
SELECT
    sa_type_cd,
    sa_type_desc,
    uom_cd,
    uom_desc,
    COUNT(*) AS determinant_rows,
    COUNT(DISTINCT bseg_id) AS bseg_count,
    SUM(total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_sq_usage_rpt_curr
GROUP BY
    sa_type_cd,
    sa_type_desc,
    uom_cd,
    uom_desc
ORDER BY
    sa_type_cd,
    SUM(total_bill_sq) DESC,
    uom_cd;

-- 4g) Determinant-count distribution by segment
SELECT
    bseg_determinant_count,
    COUNT(DISTINCT bseg_id) AS bseg_count,
    COUNT(*) AS determinant_rows,
    SUM(total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_sq_usage_rpt_curr
GROUP BY
    bseg_determinant_count
ORDER BY
    bseg_determinant_count;

-- 4h) Spot check sample multi-determinant bill segments
SELECT *
FROM cisadm.bseg_sq_usage_rpt_curr
WHERE bseg_determinant_count > 1
  AND ROWNUM <= 10;
