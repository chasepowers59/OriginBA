-- 4a) Manual first run
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
-- Should match exactly
SELECT COUNT(*) AS snapshot_count
FROM cisadm.bseg_billed_usage_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    bseg_id,
    COUNT(*) AS row_count
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY
    bseg_id
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
    SUM(CASE WHEN sole_uom_desc IS NULL AND sole_uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_uom_desc,
    SUM(CASE WHEN sole_tou_desc IS NULL AND sole_tou_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_tou_desc,
    SUM(CASE WHEN sole_sqi_desc IS NULL AND sole_sqi_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_sqi_desc,
    SUM(CASE WHEN sole_rs_desc IS NULL AND sole_rs_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_rs_desc
FROM cisadm.bseg_billed_usage_rpt_curr;

-- 4e) Billed usage and billed amount reconciliation
SELECT
    SUM(total_bill_sq) AS snap_total_bill_sq,
    SUM(total_init_sq) AS snap_total_init_sq,
    SUM(total_calc_amt) AS snap_total_calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr;

SELECT
    SUM(sq.bill_sq) AS src_total_bill_sq,
    SUM(sq.init_sq) AS src_total_init_sq
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

SELECT
    SUM(calc.calc_amt) AS src_total_calc_amt
FROM cisadm.ci_bseg_calc calc
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = calc.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

-- 4f) Determinant distribution check
SELECT
    determinant_count,
    COUNT(*) AS bseg_count,
    SUM(total_bill_sq) AS total_bill_sq
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY
    determinant_count
ORDER BY
    determinant_count;

-- 4g) Utility profile
SELECT
    utility_type_cd,
    COUNT(*) AS bseg_count,
    SUM(total_bill_sq) AS total_bill_sq,
    SUM(total_calc_amt) AS total_calc_amt
FROM cisadm.bseg_billed_usage_rpt_curr
GROUP BY
    utility_type_cd
ORDER BY
    utility_type_cd;

-- 4h) Spot check sample multi-determinant segments
SELECT *
FROM cisadm.bseg_billed_usage_rpt_curr
WHERE determinant_count > 1
  AND ROWNUM <= 5;
