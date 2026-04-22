-- Before/after validation for the rolling-window refresh change on CISADM.D1_USAGE_RPT_CURR
--
-- How to use:
-- 1. Run this script immediately before deploying the new procedure and save the results as BEFORE.
-- 2. Deploy the new procedure and run one manual refresh.
-- 3. Run this script again and save the results as AFTER.
-- 4. Compare BEFORE vs AFTER.
--
-- What should stay the same if source data does not move during the test window:
-- - whole-table snapshot row count
-- - monthly counts for history older than the rolling 12-month window
-- - duplicate-key count (should remain zero rows)
-- - rolling-window source vs snapshot parity

-- 10a) Whole-table snapshot footprint
SELECT
    COUNT(*) AS snapshot_rows,
    MIN(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm))) AS min_batch_driver_dttm,
    MAX(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm))) AS max_batch_driver_dttm,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_rpt_curr;

-- 10b) Whole-table monthly snapshot counts
SELECT
    TRUNC(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm)), 'MM') AS batch_month,
    COUNT(*) AS snapshot_rows
FROM cisadm.d1_usage_rpt_curr
GROUP BY TRUNC(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm)), 'MM')
ORDER BY batch_month;

-- 10c) Rolling 12-month source vs snapshot parity by month
WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start
    FROM dual
),
raw_months AS (
    SELECT
        TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM') AS batch_month,
        COUNT(*) AS raw_rows
    FROM cisadm.d1_usage u
    CROSS JOIN params p
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= p.window_start
    GROUP BY TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM')
),
snap_months AS (
    SELECT
        TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM') AS batch_month,
        COUNT(*) AS snapshot_rows
    FROM cisadm.d1_usage_rpt_curr s
    CROSS JOIN params p
    WHERE NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)) >= p.window_start
    GROUP BY TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM')
)
SELECT
    COALESCE(r.batch_month, s.batch_month) AS batch_month,
    NVL(r.raw_rows, 0) AS raw_rows,
    NVL(s.snapshot_rows, 0) AS snapshot_rows,
    NVL(s.snapshot_rows, 0) - NVL(r.raw_rows, 0) AS snapshot_minus_raw
FROM raw_months r
FULL OUTER JOIN snap_months s
    ON s.batch_month = r.batch_month
ORDER BY batch_month;

-- 10d) Older-than-window history retention by month
WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start
    FROM dual
)
SELECT
    TRUNC(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm)), 'MM') AS batch_month,
    COUNT(*) AS snapshot_rows_older_than_window
FROM cisadm.d1_usage_rpt_curr s
CROSS JOIN params p
WHERE NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)) < p.window_start
GROUP BY TRUNC(NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm)), 'MM')
ORDER BY batch_month;

-- 10e) Rolling 12-month bridge coverage: source vs snapshot
WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start
    FROM dual
),
raw_bridge AS (
    SELECT
        COUNT(*) AS raw_rows,
        SUM(CASE WHEN u.usg_ext_id IS NOT NULL THEN 1 ELSE 0 END) AS raw_rows_with_usg_ext_id
    FROM cisadm.d1_usage u
    CROSS JOIN params p
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= p.window_start
),
snap_bridge AS (
    SELECT
        COUNT(*) AS snapshot_rows,
        SUM(CASE WHEN s.bridge_method IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_c1_bridge,
        SUM(CASE WHEN s.sa_id IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_sa,
        SUM(CASE WHEN s.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_acct
    FROM cisadm.d1_usage_rpt_curr s
    CROSS JOIN params p
    WHERE NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)) >= p.window_start
)
SELECT
    rb.raw_rows,
    rb.raw_rows_with_usg_ext_id,
    sb.snapshot_rows,
    sb.snapshot_rows_with_c1_bridge,
    sb.snapshot_rows_with_sa,
    sb.snapshot_rows_with_acct
FROM raw_bridge rb
CROSS JOIN snap_bridge sb;

-- 10f) Duplicate key check after refresh
SELECT
    d1_usage_id,
    COUNT(*) AS row_count
FROM cisadm.d1_usage_rpt_curr
GROUP BY d1_usage_id
HAVING COUNT(*) > 1;
