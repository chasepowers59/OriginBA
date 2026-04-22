-- Before/after validation for the rolling-window refresh change on CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR
--
-- How to use:
-- 1. Run this script immediately before deploying the new nightly procedure and save the results as BEFORE.
-- 2. Deploy the new procedure and run one manual refresh.
-- 3. Run this script again and save the results as AFTER.
-- 4. Compare BEFORE vs AFTER.

-- 10a) Whole-table snapshot footprint
SELECT
    COUNT(*) AS snapshot_rows,
    SUM(NVL(quantity, 0)) AS snapshot_quantity,
    SUM(NVL(final_quantity, 0)) AS snapshot_final_quantity,
    MIN(NVL(usage_start_dttm, NVL(usage_cre_dttm, usage_status_upd_dttm))) AS min_batch_driver_dttm,
    MAX(NVL(usage_start_dttm, NVL(usage_cre_dttm, usage_status_upd_dttm))) AS max_batch_driver_dttm,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm
FROM cisadm.d1_usage_scalar_dtl_rpt_curr;

-- 10b) Whole-table monthly snapshot counts and additive quantities
SELECT
    TRUNC(NVL(usage_start_dttm, NVL(usage_cre_dttm, usage_status_upd_dttm)), 'MM') AS batch_month,
    COUNT(*) AS snapshot_rows,
    SUM(NVL(quantity, 0)) AS snapshot_quantity,
    SUM(NVL(final_quantity, 0)) AS snapshot_final_quantity
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
GROUP BY TRUNC(NVL(usage_start_dttm, NVL(usage_cre_dttm, usage_status_upd_dttm)), 'MM')
ORDER BY batch_month;

-- 10c) Rolling 12-month source vs snapshot parity by month
WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start
    FROM dual
),
raw_months AS (
    SELECT
        TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM') AS batch_month,
        COUNT(*) AS raw_rows,
        SUM(NVL(dtl.quantity, 0)) AS raw_quantity,
        SUM(NVL(dtl.final_quantity, 0)) AS raw_final_quantity
    FROM cisadm.d1_usage u
    JOIN cisadm.d1_usage_scalar_dtl dtl
        ON dtl.d1_usage_id = u.d1_usage_id
    CROSS JOIN params p
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) >= p.window_start
    GROUP BY TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM')
),
snap_months AS (
    SELECT
        TRUNC(NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)), 'MM') AS batch_month,
        COUNT(*) AS snapshot_rows,
        SUM(NVL(s.quantity, 0)) AS snapshot_quantity,
        SUM(NVL(s.final_quantity, 0)) AS snapshot_final_quantity
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
    CROSS JOIN params p
    WHERE NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)) >= p.window_start
    GROUP BY TRUNC(NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)), 'MM')
)
SELECT
    COALESCE(r.batch_month, s.batch_month) AS batch_month,
    NVL(r.raw_rows, 0) AS raw_rows,
    NVL(s.snapshot_rows, 0) AS snapshot_rows,
    NVL(s.snapshot_rows, 0) - NVL(r.raw_rows, 0) AS snapshot_minus_raw,
    NVL(r.raw_quantity, 0) AS raw_quantity,
    NVL(s.snapshot_quantity, 0) AS snapshot_quantity,
    NVL(s.snapshot_quantity, 0) - NVL(r.raw_quantity, 0) AS snapshot_quantity_minus_raw,
    NVL(r.raw_final_quantity, 0) AS raw_final_quantity,
    NVL(s.snapshot_final_quantity, 0) AS snapshot_final_quantity,
    NVL(s.snapshot_final_quantity, 0) - NVL(r.raw_final_quantity, 0) AS snapshot_final_quantity_minus_raw
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
    TRUNC(NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)), 'MM') AS batch_month,
    COUNT(*) AS snapshot_rows_older_than_window,
    SUM(NVL(s.quantity, 0)) AS snapshot_quantity_older_than_window,
    SUM(NVL(s.final_quantity, 0)) AS snapshot_final_quantity_older_than_window
FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
CROSS JOIN params p
WHERE NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)) < p.window_start
GROUP BY TRUNC(NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)), 'MM')
ORDER BY batch_month;

-- 10e) Rolling 12-month bridge and account coverage
WITH params AS (
    SELECT ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) AS window_start
    FROM dual
)
SELECT
    COUNT(*) AS snapshot_rows,
    SUM(CASE WHEN bridge_method IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_c1_bridge,
    SUM(CASE WHEN sa_id IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_sa,
    SUM(CASE WHEN acct_id IS NOT NULL THEN 1 ELSE 0 END) AS snapshot_rows_with_acct
FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
CROSS JOIN params p
WHERE NVL(s.usage_start_dttm, NVL(s.usage_cre_dttm, s.usage_status_upd_dttm)) >= p.window_start;

-- 10f) Duplicate natural-key check after refresh
SELECT
    d1_usage_id,
    seq_num,
    COUNT(*) AS row_count
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
GROUP BY d1_usage_id, seq_num
HAVING COUNT(*) > 1;
