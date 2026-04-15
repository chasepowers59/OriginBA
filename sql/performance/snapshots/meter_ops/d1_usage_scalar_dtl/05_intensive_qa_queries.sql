-- Intensive QA pack for CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR
-- Read-only. Use after refresh to prove scalar-detail parity,
-- additive quantity parity, and end-user readiness.

-- 5a) Source vs snapshot scalar-detail baseline
SELECT
    (SELECT COUNT(*)
     FROM cisadm.d1_usage_scalar_dtl dtl
     INNER JOIN cisadm.d1_usage u
         ON u.d1_usage_id = dtl.d1_usage_id
     WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL) AS source_scalar_count,
    (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr) AS snapshot_scalar_count,
    (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr) -
    (SELECT COUNT(*)
     FROM cisadm.d1_usage_scalar_dtl dtl
     INNER JOIN cisadm.d1_usage u
         ON u.d1_usage_id = dtl.d1_usage_id
     WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL) AS snapshot_minus_source
FROM dual;

-- 5b) Anti-join counts
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT dtl.d1_usage_id, dtl.seq_num
    FROM cisadm.d1_usage_scalar_dtl dtl
    INNER JOIN cisadm.d1_usage u
        ON u.d1_usage_id = dtl.d1_usage_id
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
    MINUS
    SELECT s.d1_usage_id, s.seq_num
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.d1_usage_id, s.seq_num
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
    MINUS
    SELECT dtl.d1_usage_id, dtl.seq_num
    FROM cisadm.d1_usage_scalar_dtl dtl
    INNER JOIN cisadm.d1_usage u
        ON u.d1_usage_id = dtl.d1_usage_id
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
);

-- 5c) Overall additive parity for raw and final quantity
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        SUM(NVL(dtl.quantity, 0)) AS src_quantity,
        SUM(NVL(dtl.final_quantity, 0)) AS src_final_quantity
    FROM cisadm.d1_usage_scalar_dtl dtl
    INNER JOIN cisadm.d1_usage u
        ON u.d1_usage_id = dtl.d1_usage_id
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.quantity, 0)) AS snap_quantity,
        SUM(NVL(s.final_quantity, 0)) AS snap_final_quantity
    FROM cisadm.d1_usage_scalar_dtl_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_quantity,
    snap.snap_quantity,
    snap.snap_quantity - src.src_quantity AS quantity_diff,
    src.src_final_quantity,
    snap.snap_final_quantity,
    snap.snap_final_quantity - src.src_final_quantity AS final_quantity_diff
FROM src
CROSS JOIN snap;

-- 5d) Raw-code-only audit for end-user-facing fields
WITH expected AS (
    SELECT 'DIVISION_CD' AS code_column, 'DIVISION_DESC' AS expected_desc_column, 'business translation required' AS note FROM dual UNION ALL
    SELECT 'BO_STATUS_REASON_CD', 'BO_STATUS_REASON_DESC', 'usage reason translation required' FROM dual UNION ALL
    SELECT 'US_BO_STATUS_REASON_CD', 'US_BO_STATUS_REASON_DESC', 'subscription reason translation required' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.note,
    CASE WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN' ELSE 'DESC_COLUMN_PRESENT' END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'D1_USAGE_SCALAR_DTL_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;
