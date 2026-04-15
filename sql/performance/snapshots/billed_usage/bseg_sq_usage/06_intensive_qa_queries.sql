-- Intensive QA pack for CISADM.BSEG_SQ_USAGE_RPT_CURR
-- Read-only. Use after refresh to prove completed-bill determinant parity,
-- additive quantity parity, lookup coverage, and end-user readiness.

-- 6a) Source vs snapshot determinant baseline
WITH src AS (
    SELECT COUNT(*) AS src_row_count
    FROM (
        SELECT sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
           AND bill.bill_stat_flg = 'C '
        GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    )
),
snap AS (
    SELECT COUNT(*) AS snap_row_count
    FROM cisadm.bseg_sq_usage_rpt_curr
)
SELECT
    src.src_row_count AS source_determinant_count,
    snap.snap_row_count AS snapshot_determinant_count,
    snap.snap_row_count - src.src_row_count AS snapshot_minus_source
FROM src
CROSS JOIN snap;

-- 6b) Anti-join counts
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    MINUS
    SELECT s.bseg_id, s.uom_cd, s.tou_cd, s.sqi_cd
    FROM cisadm.bseg_sq_usage_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.bseg_id, s.uom_cd, s.tou_cd, s.sqi_cd
    FROM cisadm.bseg_sq_usage_rpt_curr s
    MINUS
    SELECT sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
);

-- 6c) Overall additive quantity parity
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        SUM(NVL(det.total_init_sq, 0)) AS src_total_init_sq,
        SUM(NVL(det.total_bill_sq, 0)) AS src_total_bill_sq
    FROM (
        SELECT
            sq.bseg_id,
            sq.uom_cd,
            sq.tou_cd,
            sq.sqi_cd,
            SUM(NVL(sq.init_sq, 0)) AS total_init_sq,
            SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
           AND bill.bill_stat_flg = 'C '
        GROUP BY sq.bseg_id, sq.uom_cd, sq.tou_cd, sq.sqi_cd
    ) det
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.total_init_sq, 0)) AS snap_total_init_sq,
        SUM(NVL(s.total_bill_sq, 0)) AS snap_total_bill_sq
    FROM cisadm.bseg_sq_usage_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_total_init_sq,
    snap.snap_total_init_sq,
    snap.snap_total_init_sq - src.src_total_init_sq AS init_sq_diff,
    src.src_total_bill_sq,
    snap.snap_total_bill_sq,
    snap.snap_total_bill_sq - src.src_total_bill_sq AS bill_sq_diff
FROM src
CROSS JOIN snap;

-- 6d) Raw-code-only audit for business-facing fields that need an explicit include/exclude decision
WITH expected AS (
    SELECT 'UTILITY_TYPE_CD' AS code_column, 'UTILITY_TYPE_DESC' AS expected_desc_column, 'client-specific utility mapping may be needed' AS note FROM dual UNION ALL
    SELECT 'EST_SW', 'EST_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'CLOSING_BSEG_SW', 'CLOSING_BSEG_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'SQ_OVERRIDE_SW', 'SQ_OVERRIDE_SW_DESC', 'switch translation required' FROM dual UNION ALL
    SELECT 'ITEM_OVERRIDE_SW', 'ITEM_OVERRIDE_SW_DESC', 'switch translation required' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.note,
    CASE WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN' ELSE 'DESC_COLUMN_PRESENT' END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'BSEG_SQ_USAGE_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;
