-- 4a) Manual first run (full-history baseline)
BEGIN
    cisadm.refresh_sa_aged_bal_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.sa_aged_bal_rpt_curr;

WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
    HAVING SUM(ft.cur_amt) > 0
)
SELECT COUNT(*) AS source_count
FROM governed_ft gf
JOIN cisadm.ci_sa sa
  ON sa.sa_id = gf.sa_id
 AND sa.sa_status_flg = '20';

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    sa_id,
    COUNT(*) AS row_count
FROM cisadm.sa_aged_bal_rpt_curr
GROUP BY sa_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN debt_cl_desc IS NULL AND debt_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_debt_cl_desc,
    SUM(CASE WHEN bill_cyc_desc IS NULL AND bill_cyc_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_bill_cyc_desc,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN cust_cl_desc IS NULL AND cust_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_cust_cl_desc,
    SUM(CASE WHEN acct_mgmt_grp_desc IS NULL AND acct_mgmt_grp_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_acct_mgmt_grp_desc,
    SUM(CASE WHEN state_desc IS NULL AND state IS NOT NULL THEN 1 ELSE 0 END) AS missing_state_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.sa_aged_bal_rpt_curr;

-- 4e) Debt reconciliation
SELECT
    SUM(total_debt) AS snap_total_debt,
    SUM(debt_0_30) AS snap_debt_0_30,
    SUM(debt_31_60) AS snap_debt_31_60,
    SUM(debt_61_90) AS snap_debt_61_90,
    SUM(debt_over_90) AS snap_debt_over_90
FROM cisadm.sa_aged_bal_rpt_curr;

WITH governed_ft AS (
    SELECT
        ft.sa_id,
        SUM(ft.cur_amt) AS total_debt,
        SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt <= 30 THEN ft.cur_amt ELSE 0 END) AS debt_0_30,
        SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt BETWEEN 31 AND 60 THEN ft.cur_amt ELSE 0 END) AS debt_31_60,
        SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt BETWEEN 61 AND 90 THEN ft.cur_amt ELSE 0 END) AS debt_61_90,
        SUM(CASE WHEN TRUNC(SYSDATE) - ft.ars_dt > 90 THEN ft.cur_amt ELSE 0 END) AS debt_over_90
    FROM cisadm.ci_ft ft
    WHERE ft.freeze_sw = 'Y'
      AND ft.not_in_ars_sw = 'N'
      AND ft.ft_type_flg NOT IN ('PS', 'PX')
      AND ft.ars_dt IS NOT NULL
    GROUP BY ft.sa_id
    HAVING SUM(ft.cur_amt) > 0
)
SELECT
    SUM(gf.total_debt) AS src_total_debt,
    SUM(gf.debt_0_30) AS src_debt_0_30,
    SUM(gf.debt_31_60) AS src_debt_31_60,
    SUM(gf.debt_61_90) AS src_debt_61_90,
    SUM(gf.debt_over_90) AS src_debt_over_90
FROM governed_ft gf
JOIN cisadm.ci_sa sa
  ON sa.sa_id = gf.sa_id
 AND sa.sa_status_flg = '20';

-- 4f) Snapshot should only contain positive-debt service agreements
SELECT *
FROM cisadm.sa_aged_bal_rpt_curr
WHERE total_debt <= 0;

-- 4g) Debt distribution by SA type
SELECT
    sa_type_cd,
    sa_type_desc,
    debt_cl_cd,
    debt_cl_desc,
    COUNT(*) AS sa_count,
    SUM(total_debt) AS total_debt
FROM cisadm.sa_aged_bal_rpt_curr
GROUP BY
    sa_type_cd,
    sa_type_desc,
    debt_cl_cd,
    debt_cl_desc
ORDER BY
    total_debt DESC NULLS LAST,
    sa_type_cd;

-- 4h) Premise coverage
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN char_prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_char_prem_id,
    SUM(CASE WHEN prem_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_resolved_prem_id,
    SUM(CASE WHEN address1 IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_address1
FROM cisadm.sa_aged_bal_rpt_curr;

-- 4i) Spot-check largest SA debt rows
SELECT *
FROM (
    SELECT *
    FROM cisadm.sa_aged_bal_rpt_curr
    ORDER BY total_debt DESC
)
WHERE ROWNUM <= 10;
