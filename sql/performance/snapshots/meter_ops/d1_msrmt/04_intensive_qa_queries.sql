-- Intensive QA pack for CISADM.D1_MSRMT_RPT_CURR
-- Read-only. Use after refresh to prove measurement-grain parity,
-- service-point/install context coverage, and end-user readiness.

-- 4a) Source vs snapshot baseline
SELECT
    (SELECT COUNT(*) FROM cisadm.d1_msrmt) AS source_measurement_count,
    (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr) AS snapshot_measurement_count,
    (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr) -
    (SELECT COUNT(*) FROM cisadm.d1_msrmt) AS snapshot_minus_source
FROM dual;

-- 4b) Natural-key duplicates in snapshot
SELECT
    measr_comp_id,
    msrmt_dttm,
    COUNT(*) AS row_count
FROM cisadm.d1_msrmt_rpt_curr
GROUP BY measr_comp_id, msrmt_dttm
HAVING COUNT(*) > 1;

-- 4c) Anti-join counts
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT msrmt.measr_comp_id, msrmt.msrmt_dttm
    FROM cisadm.d1_msrmt msrmt
    MINUS
    SELECT s.measr_comp_id, s.msrmt_dttm
    FROM cisadm.d1_msrmt_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.measr_comp_id, s.msrmt_dttm
    FROM cisadm.d1_msrmt_rpt_curr s
    MINUS
    SELECT msrmt.measr_comp_id, msrmt.msrmt_dttm
    FROM cisadm.d1_msrmt msrmt
);

-- 4d) Service-point/install context coverage
WITH src AS (
    SELECT
        COUNT(*) AS src_rows,
        SUM(CASE WHEN mc.measr_comp_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_mc,
        SUM(CASE WHEN ie.install_evt_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_install_evt,
        SUM(CASE WHEN sp.d1_sp_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_sp
    FROM cisadm.d1_msrmt msrmt
    LEFT JOIN cisadm.d1_measr_comp mc
        ON mc.measr_comp_id = msrmt.measr_comp_id
    LEFT JOIN cisadm.d1_install_evt ie
        ON ie.device_config_id = mc.device_config_id
    LEFT JOIN cisadm.d1_sp sp
        ON sp.d1_sp_id = ie.d1_sp_id
),
snap AS (
    SELECT
        COUNT(*) AS snap_rows,
        SUM(CASE WHEN measr_comp_type_cd IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_mc,
        SUM(CASE WHEN install_evt_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_install_evt,
        SUM(CASE WHEN d1_sp_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_sp
    FROM cisadm.d1_msrmt_rpt_curr
)
SELECT
    src.src_rows,
    snap.snap_rows,
    snap.snap_rows - src.src_rows AS row_diff,
    src.src_rows_with_mc,
    snap.snap_rows_with_mc,
    snap.snap_rows_with_mc - src.src_rows_with_mc AS mc_diff,
    src.src_rows_with_install_evt,
    snap.snap_rows_with_install_evt,
    snap.snap_rows_with_install_evt - src.src_rows_with_install_evt AS install_evt_diff,
    src.src_rows_with_sp,
    snap.snap_rows_with_sp,
    snap.snap_rows_with_sp - src.src_rows_with_sp AS sp_diff
FROM src
CROSS JOIN snap;

-- 4e) Raw-code-only audit for end-user-facing fields
WITH expected AS (
    SELECT 'DIVISION_CD' AS code_column, 'DIVISION_DESC' AS expected_desc_column, 'business translation required' AS note FROM dual UNION ALL
    SELECT 'MKT_CD', 'MKT_DESC', 'business translation required' FROM dual UNION ALL
    SELECT 'MSRMT_BO_STATUS_REASON_CD', 'MSRMT_BO_STATUS_REASON_DESC', 'measurement reason translation required' FROM dual UNION ALL
    SELECT 'IMD_BO_STATUS_REASON_CD', 'IMD_BO_STATUS_REASON_DESC', 'imd reason translation required' FROM dual UNION ALL
    SELECT 'MC_BO_STATUS_REASON_CD', 'MC_BO_STATUS_REASON_DESC', 'measuring component reason translation required' FROM dual UNION ALL
    SELECT 'SP_BO_STATUS_REASON_CD', 'SP_BO_STATUS_REASON_DESC', 'service point reason translation required' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.note,
    CASE WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN' ELSE 'DESC_COLUMN_PRESENT' END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'D1_MSRMT_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;
