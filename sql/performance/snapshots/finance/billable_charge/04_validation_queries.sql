-- 4a) Manual first run (full-history baseline)
BEGIN
    cisadm.refresh_billable_charge_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.billable_charge_rpt_curr;

SELECT COUNT(*) AS source_line_count
FROM cisadm.ci_b_chg_line bcl
INNER JOIN cisadm.ci_bill_chg bc
    ON bc.billable_chg_id = bcl.billable_chg_id;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    billable_chg_id,
    line_seq,
    COUNT(*) AS row_count
FROM cisadm.billable_charge_rpt_curr
GROUP BY
    billable_chg_id,
    line_seq
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN billable_chg_stat_desc IS NULL AND billable_chg_stat IS NOT NULL THEN 1 ELSE 0 END) AS missing_billable_chg_stat_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN charge_amt IS NULL THEN 1 ELSE 0 END) AS missing_charge_amt
FROM cisadm.billable_charge_rpt_curr;

-- 4e) Charge amount reconciliation
SELECT
    SUM(charge_amt) AS snap_total_charge_amt,
    COUNT(DISTINCT billable_chg_id) AS snap_distinct_charge_count,
    COUNT(DISTINCT sa_id) AS snap_distinct_sa_count
FROM cisadm.billable_charge_rpt_curr;

SELECT
    SUM(bcl.charge_amt) AS src_total_charge_amt,
    COUNT(DISTINCT bcl.billable_chg_id) AS src_distinct_charge_count,
    COUNT(DISTINCT bc.sa_id) AS src_distinct_sa_count
FROM cisadm.ci_b_chg_line bcl
INNER JOIN cisadm.ci_bill_chg bc
    ON bc.billable_chg_id = bcl.billable_chg_id;

-- 4f) Rolling-window profile
SELECT
    COUNT(*) AS rows_in_6mo_window
FROM cisadm.billable_charge_rpt_curr
WHERE charge_start_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
   OR charge_end_dt IS NULL
   OR charge_end_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6);

-- 4g) Status profile
SELECT
    billable_chg_stat,
    billable_chg_stat_desc,
    COUNT(*) AS line_count,
    SUM(charge_amt) AS total_charge_amt
FROM cisadm.billable_charge_rpt_curr
GROUP BY
    billable_chg_stat,
    billable_chg_stat_desc
ORDER BY
    line_count DESC,
    billable_chg_stat;

-- 4h) Spot-check largest charge lines
SELECT *
FROM (
    SELECT *
    FROM cisadm.billable_charge_rpt_curr
    ORDER BY charge_amt DESC NULLS LAST
)
WHERE ROWNUM <= 10;
