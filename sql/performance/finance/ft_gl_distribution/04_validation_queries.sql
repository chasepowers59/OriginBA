-- 4a) Manual first run
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/

-- 4b) Row count parity (snapshot vs. source)
-- Should match exactly
SELECT COUNT(*) AS snapshot_count
FROM cisadm.ft_gl_distribution_rpt_curr;

SELECT COUNT(*) AS source_count
FROM cisadm.ci_ft_gl gl
INNER JOIN cisadm.ci_ft ft
    ON ft.ft_id = gl.ft_id
WHERE ft.redundant_sw = 'N';

-- 4c) Duplicate key check (should return 0 rows)
SELECT
    ft_id,
    gl_seq_nbr,
    COUNT(*) AS row_count
FROM cisadm.ft_gl_distribution_rpt_curr
GROUP BY
    ft_id,
    gl_seq_nbr
HAVING COUNT(*) > 1;

-- 4d) Null coverage check (verify lookups are resolving descriptions)
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN ft_type_flg_desc IS NULL THEN 1 ELSE 0 END) AS missing_ft_type_desc,
    SUM(CASE WHEN gl_distrib_status_desc IS NULL AND gl_distrib_status IS NOT NULL THEN 1 ELSE 0 END) AS missing_gl_status_desc,
    SUM(CASE WHEN dst_desc IS NULL AND dst_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_dst_desc,
    SUM(CASE WHEN sa_status_desc IS NULL AND sa_status_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_status_desc,
    SUM(CASE WHEN sa_type_desc IS NULL AND sa_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sa_type_desc,
    SUM(CASE WHEN customer_name_upr IS NULL AND acct_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_customer_name,
    SUM(CASE WHEN balancing_stat_desc IS NULL AND balancing_stat_flg IS NOT NULL THEN 1 ELSE 0 END) AS missing_balancing_status_desc,
    SUM(CASE WHEN freeze_user_name IS NULL AND freeze_user_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_freeze_user_name
FROM cisadm.ft_gl_distribution_rpt_curr;

-- 4e) Amount reconciliation (snapshot GL totals must match source)
SELECT
    SUM(gl_amount) AS snap_gl_amount,
    SUM(statistic_amount) AS snap_statistic_amount
FROM cisadm.ft_gl_distribution_rpt_curr;

SELECT
    SUM(gl.amount) AS src_gl_amount,
    SUM(gl.statistic_amount) AS src_statistic_amount
FROM cisadm.ci_ft_gl gl
INNER JOIN cisadm.ci_ft ft
    ON ft.ft_id = gl.ft_id
WHERE ft.redundant_sw = 'N';

-- 4e1) Exact statistic amount diff check
-- Oracle requires the aggregates to be isolated before comparing them.
WITH snap AS (
    SELECT SUM(statistic_amount) AS snap_stat_amt
    FROM cisadm.ft_gl_distribution_rpt_curr
),
src AS (
    SELECT SUM(gl.statistic_amount) AS src_stat_amt
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
)
SELECT
    snap.snap_stat_amt,
    src.src_stat_amt,
    snap.snap_stat_amt - src.src_stat_amt AS diff
FROM snap
CROSS JOIN src;

-- 4f) FT type distribution inside GL accounts
SELECT
    gl_acct,
    dst_id,
    ft_type_flg,
    ft_type_flg_desc,
    COUNT(*) AS gl_line_count,
    COUNT(DISTINCT ft_id) AS ft_count,
    SUM(gl_amount) AS gl_amount
FROM cisadm.ft_gl_distribution_rpt_curr
GROUP BY
    gl_acct,
    dst_id,
    ft_type_flg,
    ft_type_flg_desc
ORDER BY
    gl_acct,
    dst_id,
    ft_type_flg;

-- 4g) Spot check sample rows
SELECT *
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE gl_acct IS NOT NULL
  AND ROWNUM <= 5;

-- 4h) Adjustment trace coverage
SELECT
    COUNT(*) AS ad_gl_rows,
    SUM(CASE WHEN adj_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_adj_id,
    SUM(CASE WHEN xfer_adj_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_xfer_adj_id,
    SUM(CASE WHEN per_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_per_id,
    SUM(CASE WHEN customer_name_upr IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_customer_name
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE ft_type_flg = 'AD';
