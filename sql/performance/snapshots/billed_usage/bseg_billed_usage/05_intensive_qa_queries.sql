-- Intensive QA pack for CISADM.BSEG_BILLED_USAGE_RPT_CURR
-- Read-only. Use after refresh to prove completed-bill population parity,
-- additive quantity/amount parity, lookup coverage, and end-user readiness.

-- 5a) Source vs snapshot completed-segment baseline
SELECT
    (SELECT COUNT(*)
     FROM cisadm.ci_bseg bseg
     INNER JOIN cisadm.ci_bill bill
         ON bill.bill_id = bseg.bill_id
     WHERE bill.bill_stat_flg = 'C ') AS source_completed_bseg_count,
    (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) AS snapshot_bseg_count,
    (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) -
    (SELECT COUNT(*)
     FROM cisadm.ci_bseg bseg
     INNER JOIN cisadm.ci_bill bill
         ON bill.bill_id = bseg.bill_id
     WHERE bill.bill_stat_flg = 'C ') AS snapshot_minus_source
FROM dual;

-- 5b) Anti-join counts
SELECT COUNT(*) AS source_bsegs_missing_in_snapshot
FROM (
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    MINUS
    SELECT s.bseg_id
    FROM cisadm.bseg_billed_usage_rpt_curr s
);

SELECT COUNT(*) AS snapshot_bsegs_not_in_source
FROM (
    SELECT s.bseg_id
    FROM cisadm.bseg_billed_usage_rpt_curr s
    MINUS
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
     WHERE bill.bill_stat_flg = 'C '
);

-- 5b1) Sample completed bill segments missing in snapshot
SELECT *
FROM (
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    MINUS
    SELECT s.bseg_id
    FROM cisadm.bseg_billed_usage_rpt_curr s
)
FETCH FIRST 25 ROWS ONLY;

-- 5b2) Sample snapshot rows not in completed-bill source
SELECT *
FROM (
    SELECT s.bseg_id
    FROM cisadm.bseg_billed_usage_rpt_curr s
    MINUS
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
)
FETCH FIRST 25 ROWS ONLY;

-- 5c) Overall additive parity for billed usage and calc amount
WITH src AS (
    SELECT
        COUNT(*) AS src_row_count,
        src_sq.src_total_bill_sq,
        src_sq.src_total_init_sq,
        src_calc.src_total_calc_amt
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    CROSS JOIN (
        SELECT
            SUM(NVL(sq.bill_sq, 0)) AS src_total_bill_sq,
            SUM(NVL(sq.init_sq, 0)) AS src_total_init_sq
        FROM cisadm.ci_bseg_sq sq
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = sq.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
        WHERE bill.bill_stat_flg = 'C '
    ) src_sq
    CROSS JOIN (
        SELECT
            SUM(NVL(calc.calc_amt, 0)) AS src_total_calc_amt
        FROM cisadm.ci_bseg_calc calc
        INNER JOIN cisadm.ci_bseg bseg
            ON bseg.bseg_id = calc.bseg_id
        INNER JOIN cisadm.ci_bill bill
            ON bill.bill_id = bseg.bill_id
        WHERE bill.bill_stat_flg = 'C '
    ) src_calc
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        src_sq.src_total_bill_sq,
        src_sq.src_total_init_sq,
        src_calc.src_total_calc_amt
),
snap AS (
    SELECT
        COUNT(*) AS snap_row_count,
        SUM(NVL(s.total_bill_sq, 0)) AS snap_total_bill_sq,
        SUM(NVL(s.total_init_sq, 0)) AS snap_total_init_sq,
        SUM(NVL(s.total_calc_amt, 0)) AS snap_total_calc_amt
    FROM cisadm.bseg_billed_usage_rpt_curr s
)
SELECT
    src.src_row_count,
    snap.snap_row_count,
    snap.snap_row_count - src.src_row_count AS row_count_diff,
    src.src_total_bill_sq,
    snap.snap_total_bill_sq,
    snap.snap_total_bill_sq - src.src_total_bill_sq AS total_bill_sq_diff,
    src.src_total_init_sq,
    snap.snap_total_init_sq,
    snap.snap_total_init_sq - src.src_total_init_sq AS total_init_sq_diff,
    src.src_total_calc_amt,
    snap.snap_total_calc_amt,
    snap.snap_total_calc_amt - src.src_total_calc_amt AS total_calc_amt_diff
FROM src
CROSS JOIN snap;

-- 5d) Aggregated child parity
WITH src AS (
    SELECT
        COUNT(*) AS src_bsegs,
        SUM(CASE WHEN sq_agg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_sq,
        SUM(CASE WHEN read_agg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_read,
        SUM(CASE WHEN calc_agg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_calc
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
       AND bill.bill_stat_flg = 'C '
    LEFT JOIN (SELECT DISTINCT bseg_id FROM cisadm.ci_bseg_sq) sq_agg
        ON sq_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (SELECT DISTINCT bseg_id FROM cisadm.ci_bseg_read) read_agg
        ON read_agg.bseg_id = bseg.bseg_id
    LEFT JOIN (SELECT DISTINCT bseg_id FROM cisadm.ci_bseg_calc) calc_agg
        ON calc_agg.bseg_id = bseg.bseg_id
),
snap AS (
    SELECT
        COUNT(*) AS snap_bsegs,
        SUM(CASE WHEN sq_line_count IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_sq,
        SUM(CASE WHEN read_line_count IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_read,
        SUM(CASE WHEN calc_header_count IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_calc
    FROM cisadm.bseg_billed_usage_rpt_curr
)
SELECT
    src.src_bsegs,
    snap.snap_bsegs,
    snap.snap_bsegs - src.src_bsegs AS bseg_diff,
    src.src_rows_with_sq,
    snap.snap_rows_with_sq,
    snap.snap_rows_with_sq - src.src_rows_with_sq AS sq_diff,
    src.src_rows_with_read,
    snap.snap_rows_with_read,
    snap.snap_rows_with_read - src.src_rows_with_read AS read_diff,
    src.src_rows_with_calc,
    snap.snap_rows_with_calc,
    snap.snap_rows_with_calc - src.src_rows_with_calc AS calc_diff
FROM src
CROSS JOIN snap;

-- 5d1) Sole-value description coverage only where single-valued context exists
SELECT
    COUNT(*) AS rows_with_one_determinant,
    SUM(CASE WHEN sole_uom_cd IS NOT NULL AND sole_uom_desc IS NULL THEN 1 ELSE 0 END) AS missing_sole_uom_desc_when_required,
    SUM(CASE WHEN sole_tou_cd IS NOT NULL AND sole_tou_desc IS NULL THEN 1 ELSE 0 END) AS missing_sole_tou_desc_when_required,
    SUM(CASE WHEN sole_sqi_cd IS NOT NULL AND sole_sqi_desc IS NULL THEN 1 ELSE 0 END) AS missing_sole_sqi_desc_when_required
FROM cisadm.bseg_billed_usage_rpt_curr
WHERE determinant_count = 1;

SELECT
    COUNT(*) AS rows_with_one_rate,
    SUM(CASE WHEN sole_rs_cd IS NOT NULL AND sole_rs_desc IS NULL THEN 1 ELSE 0 END) AS missing_sole_rs_desc_when_required
FROM cisadm.bseg_billed_usage_rpt_curr
WHERE rs_count = 1;

-- 5e) Raw-code-only audit for business-facing fields that need an explicit include/exclude decision
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
   AND c.table_name = 'BSEG_BILLED_USAGE_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;
