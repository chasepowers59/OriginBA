-- 4a) Manual first run
BEGIN
    cisadm.refresh_acct_debt_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
SELECT COUNT(*) AS snapshot_count
FROM cisadm.acct_debt_rpt_curr;

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
),
debt_by_acct AS (
    SELECT
        sa.acct_id,
        SUM(gf.total_debt) AS total_debt
    FROM governed_ft gf
    JOIN cisadm.ci_sa sa
      ON sa.sa_id = gf.sa_id
     AND sa.sa_status_flg = '20'
    GROUP BY sa.acct_id
    HAVING SUM(gf.total_debt) > 0
)
SELECT COUNT(*) AS source_count
FROM debt_by_acct;

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    acct_id,
    COUNT(*) AS row_count
FROM cisadm.acct_debt_rpt_curr
GROUP BY acct_id
HAVING COUNT(*) > 1;

-- 4d) Null coverage check
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN coll_cl_desc IS NULL AND coll_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_coll_cl_desc,
    SUM(CASE WHEN sole_debt_cl_desc IS NULL AND sole_debt_cl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sole_debt_cl_desc,
    SUM(CASE WHEN latest_coll_status_desc IS NULL AND latest_coll_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_coll_status_desc,
    SUM(CASE WHEN latest_coll_proc_tmpl_desc IS NULL AND latest_coll_proc_tmpl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_coll_proc_tmpl_desc,
    SUM(CASE WHEN latest_wo_status_desc IS NULL AND latest_wo_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_wo_status_desc,
    SUM(CASE WHEN latest_wo_proc_tmpl_desc IS NULL AND latest_wo_proc_tmpl_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_latest_wo_proc_tmpl_desc,
    SUM(CASE WHEN customer_name IS NULL THEN 1 ELSE 0 END) AS missing_customer_name
FROM cisadm.acct_debt_rpt_curr;

-- 4e) Debt reconciliation
SELECT
    SUM(total_debt) AS snap_total_debt,
    SUM(debt_0_30) AS snap_debt_0_30,
    SUM(debt_31_60) AS snap_debt_31_60,
    SUM(debt_61_90) AS snap_debt_61_90,
    SUM(debt_over_90) AS snap_debt_over_90
FROM cisadm.acct_debt_rpt_curr;

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
),
debt_by_acct AS (
    SELECT
        sa.acct_id,
        SUM(gf.total_debt) AS total_debt,
        SUM(gf.debt_0_30) AS debt_0_30,
        SUM(gf.debt_31_60) AS debt_31_60,
        SUM(gf.debt_61_90) AS debt_61_90,
        SUM(gf.debt_over_90) AS debt_over_90
    FROM governed_ft gf
    JOIN cisadm.ci_sa sa
      ON sa.sa_id = gf.sa_id
     AND sa.sa_status_flg = '20'
    GROUP BY sa.acct_id
    HAVING SUM(gf.total_debt) > 0
)
SELECT
    SUM(total_debt) AS src_total_debt,
    SUM(debt_0_30) AS src_debt_0_30,
    SUM(debt_31_60) AS src_debt_31_60,
    SUM(debt_61_90) AS src_debt_61_90,
    SUM(debt_over_90) AS src_debt_over_90
FROM debt_by_acct;

-- 4f) Snapshot should only contain positive-debt accounts
SELECT *
FROM cisadm.acct_debt_rpt_curr
WHERE total_debt <= 0;

-- 4g) Process linkage sanity checks
SELECT
    COUNT(*) AS rows_with_coll_proc_count_but_no_latest_coll_proc
FROM cisadm.acct_debt_rpt_curr
WHERE NVL(coll_proc_count, 0) > 0
  AND latest_coll_proc_id IS NULL;

SELECT
    COUNT(*) AS rows_with_wo_proc_count_but_no_latest_wo_proc
FROM cisadm.acct_debt_rpt_curr
WHERE NVL(wo_proc_count, 0) > 0
  AND latest_wo_proc_id IS NULL;

-- 4h) Debt distribution by collection class
SELECT
    coll_cl_cd,
    coll_cl_desc,
    COUNT(*) AS acct_count,
    SUM(total_debt) AS total_debt
FROM cisadm.acct_debt_rpt_curr
GROUP BY
    coll_cl_cd,
    coll_cl_desc
ORDER BY
    total_debt DESC NULLS LAST,
    coll_cl_cd;

-- 4i) Debt-class profile
SELECT
    debt_cl_count,
    sole_debt_cl_cd,
    sole_debt_cl_desc,
    COUNT(*) AS acct_count,
    SUM(total_debt) AS total_debt
FROM cisadm.acct_debt_rpt_curr
GROUP BY
    debt_cl_count,
    sole_debt_cl_cd,
    sole_debt_cl_desc
ORDER BY
    acct_count DESC,
    debt_cl_count,
    sole_debt_cl_cd;

-- 4j) Spot-check largest debt accounts
SELECT *
FROM (
    SELECT *
    FROM cisadm.acct_debt_rpt_curr
    ORDER BY total_debt DESC
)
WHERE ROWNUM <= 10;
