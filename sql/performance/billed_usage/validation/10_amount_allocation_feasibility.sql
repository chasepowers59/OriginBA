-- 10_amount_allocation_feasibility.sql
-- Purpose:
--   Test whether billed amount can be allocated defensibly from CI_BSEG_CALC_LN
--   down to BSEG_SQ determinant grain using (BSEG_ID, UOM_CD, TOU_CD, SQI_CD).
--
-- Read-only:
--   SELECT-only. No DDL, DML, or explain plan.
--
-- What to look for:
--   1) CI_BSEG_CALC header amounts should reconcile closely to CI_BSEG_CALC_LN sums.
--   2) Determinant keys from CI_BSEG_SQ should match determinant keys on CI_BSEG_CALC_LN.
--   3) If many segments have CALC_ONLY determinant rows, billed dollars likely include
--      fixed or non-usage components that cannot be assigned to usage determinants directly.

set pagesize 50000
set linesize 240
set trimspool on

-- 10a) Header-to-line billed amount parity on completed bill segments
WITH completed_bseg AS (
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
),
calc_hdr AS (
    SELECT
        calc.bseg_id,
        COUNT(*) AS calc_header_count,
        SUM(NVL(calc.calc_amt, 0)) AS calc_header_amt
    FROM cisadm.ci_bseg_calc calc
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = calc.bseg_id
    GROUP BY
        calc.bseg_id
),
calc_ln AS (
    SELECT
        ln.bseg_id,
        COUNT(*) AS calc_line_count,
        SUM(NVL(ln.calc_amt, 0)) AS calc_line_amt
    FROM cisadm.ci_bseg_calc_ln ln
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = ln.bseg_id
    GROUP BY
        ln.bseg_id
)
SELECT
    COUNT(*) AS total_completed_bseg,
    SUM(CASE WHEN hdr.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS bseg_with_calc_headers,
    SUM(CASE WHEN ln.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS bseg_with_calc_lines,
    SUM(CASE
            WHEN ABS(NVL(hdr.calc_header_amt, 0) - NVL(ln.calc_line_amt, 0)) < 0.000001
            THEN 1
            ELSE 0
        END) AS bseg_with_header_line_parity,
    SUM(NVL(hdr.calc_header_amt, 0)) AS total_calc_header_amt,
    SUM(NVL(ln.calc_line_amt, 0)) AS total_calc_line_amt,
    SUM(NVL(hdr.calc_header_amt, 0) - NVL(ln.calc_line_amt, 0)) AS total_header_minus_line_amt
FROM completed_bseg cb
LEFT JOIN calc_hdr hdr
    ON hdr.bseg_id = cb.bseg_id
LEFT JOIN calc_ln ln
    ON ln.bseg_id = cb.bseg_id;

-- 10b) Determinant-key coverage between billed usage and calc lines
WITH completed_bseg AS (
    SELECT bseg.bseg_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
),
sq_det AS (
    SELECT
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~') AS uom_cd,
        NVL(TRIM(sq.tou_cd), '~') AS tou_cd,
        NVL(TRIM(sq.sqi_cd), '~') AS sqi_cd,
        COUNT(*) AS sq_line_count,
        SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = sq.bseg_id
    GROUP BY
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~'),
        NVL(TRIM(sq.tou_cd), '~'),
        NVL(TRIM(sq.sqi_cd), '~')
),
calc_det AS (
    SELECT
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~') AS uom_cd,
        NVL(TRIM(ln.tou_cd), '~') AS tou_cd,
        NVL(TRIM(ln.sqi_cd), '~') AS sqi_cd,
        COUNT(*) AS calc_line_count,
        SUM(NVL(ln.calc_amt, 0)) AS total_calc_amt
    FROM cisadm.ci_bseg_calc_ln ln
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = ln.bseg_id
    GROUP BY
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~'),
        NVL(TRIM(ln.tou_cd), '~'),
        NVL(TRIM(ln.sqi_cd), '~')
),
joined_det AS (
    SELECT
        COALESCE(sq.bseg_id, calc.bseg_id) AS bseg_id,
        COALESCE(sq.uom_cd, calc.uom_cd) AS uom_cd,
        COALESCE(sq.tou_cd, calc.tou_cd) AS tou_cd,
        COALESCE(sq.sqi_cd, calc.sqi_cd) AS sqi_cd,
        sq.sq_line_count,
        sq.total_bill_sq,
        calc.calc_line_count,
        calc.total_calc_amt,
        CASE
            WHEN sq.bseg_id IS NOT NULL AND calc.bseg_id IS NOT NULL THEN 'MATCHED'
            WHEN sq.bseg_id IS NOT NULL AND calc.bseg_id IS NULL THEN 'SQ_ONLY'
            WHEN sq.bseg_id IS NULL AND calc.bseg_id IS NOT NULL THEN 'CALC_ONLY'
        END AS match_status
    FROM sq_det sq
    FULL OUTER JOIN calc_det calc
        ON calc.bseg_id = sq.bseg_id
       AND calc.uom_cd = sq.uom_cd
       AND calc.tou_cd = sq.tou_cd
       AND calc.sqi_cd = sq.sqi_cd
)
SELECT
    match_status,
    COUNT(*) AS determinant_key_count,
    SUM(NVL(sq_line_count, 0)) AS sq_line_count,
    SUM(NVL(calc_line_count, 0)) AS calc_line_count,
    SUM(NVL(total_bill_sq, 0)) AS total_bill_sq,
    SUM(NVL(total_calc_amt, 0)) AS total_calc_amt
FROM joined_det
GROUP BY
    match_status
ORDER BY
    match_status;

-- 10c) Segment-level allocation feasibility classification
WITH completed_bseg AS (
    SELECT
        bseg.bseg_id,
        bseg.sa_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
),
calc_hdr AS (
    SELECT
        calc.bseg_id,
        SUM(NVL(calc.calc_amt, 0)) AS calc_header_amt
    FROM cisadm.ci_bseg_calc calc
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = calc.bseg_id
    GROUP BY
        calc.bseg_id
),
calc_ln AS (
    SELECT
        ln.bseg_id,
        SUM(NVL(ln.calc_amt, 0)) AS calc_line_amt
    FROM cisadm.ci_bseg_calc_ln ln
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = ln.bseg_id
    GROUP BY
        ln.bseg_id
),
sq_det AS (
    SELECT
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~') AS uom_cd,
        NVL(TRIM(sq.tou_cd), '~') AS tou_cd,
        NVL(TRIM(sq.sqi_cd), '~') AS sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = sq.bseg_id
    GROUP BY
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~'),
        NVL(TRIM(sq.tou_cd), '~'),
        NVL(TRIM(sq.sqi_cd), '~')
),
calc_det AS (
    SELECT
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~') AS uom_cd,
        NVL(TRIM(ln.tou_cd), '~') AS tou_cd,
        NVL(TRIM(ln.sqi_cd), '~') AS sqi_cd
    FROM cisadm.ci_bseg_calc_ln ln
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = ln.bseg_id
    GROUP BY
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~'),
        NVL(TRIM(ln.tou_cd), '~'),
        NVL(TRIM(ln.sqi_cd), '~')
),
joined_det AS (
    SELECT
        COALESCE(sq.bseg_id, calc.bseg_id) AS bseg_id,
        CASE
            WHEN sq.bseg_id IS NOT NULL AND calc.bseg_id IS NOT NULL THEN 'MATCHED'
            WHEN sq.bseg_id IS NOT NULL AND calc.bseg_id IS NULL THEN 'SQ_ONLY'
            WHEN sq.bseg_id IS NULL AND calc.bseg_id IS NOT NULL THEN 'CALC_ONLY'
        END AS match_status
    FROM sq_det sq
    FULL OUTER JOIN calc_det calc
        ON calc.bseg_id = sq.bseg_id
       AND calc.uom_cd = sq.uom_cd
       AND calc.tou_cd = sq.tou_cd
       AND calc.sqi_cd = sq.sqi_cd
),
seg_class AS (
    SELECT
        cb.bseg_id,
        cb.sa_id,
        NVL(hdr.calc_header_amt, 0) AS calc_header_amt,
        NVL(ln.calc_line_amt, 0) AS calc_line_amt,
        SUM(CASE WHEN det.match_status = 'MATCHED' THEN 1 ELSE 0 END) AS matched_det_count,
        SUM(CASE WHEN det.match_status = 'SQ_ONLY' THEN 1 ELSE 0 END) AS sq_only_det_count,
        SUM(CASE WHEN det.match_status = 'CALC_ONLY' THEN 1 ELSE 0 END) AS calc_only_det_count
    FROM completed_bseg cb
    LEFT JOIN calc_hdr hdr
        ON hdr.bseg_id = cb.bseg_id
    LEFT JOIN calc_ln ln
        ON ln.bseg_id = cb.bseg_id
    LEFT JOIN joined_det det
        ON det.bseg_id = cb.bseg_id
    GROUP BY
        cb.bseg_id,
        cb.sa_id,
        NVL(hdr.calc_header_amt, 0),
        NVL(ln.calc_line_amt, 0)
)
SELECT
    CASE
        WHEN ABS(calc_header_amt - calc_line_amt) >= 0.000001 THEN 'HEADER_LINE_MISMATCH'
        WHEN sq_only_det_count = 0 AND calc_only_det_count = 0 THEN 'DIRECT_DETERMINANT_ALLOCATION_READY'
        WHEN sq_only_det_count = 0 AND calc_only_det_count > 0 THEN 'CALC_HAS_NON_SQ_DETERMINANTS'
        WHEN sq_only_det_count > 0 AND calc_only_det_count = 0 THEN 'SQ_HAS_NO_CALC_MATCH'
        ELSE 'MIXED_DETERMINANT_MISMATCH'
    END AS allocation_status,
    COUNT(*) AS bseg_count,
    SUM(calc_header_amt) AS total_calc_header_amt,
    SUM(calc_line_amt) AS total_calc_line_amt
FROM seg_class
GROUP BY
    CASE
        WHEN ABS(calc_header_amt - calc_line_amt) >= 0.000001 THEN 'HEADER_LINE_MISMATCH'
        WHEN sq_only_det_count = 0 AND calc_only_det_count = 0 THEN 'DIRECT_DETERMINANT_ALLOCATION_READY'
        WHEN sq_only_det_count = 0 AND calc_only_det_count > 0 THEN 'CALC_HAS_NON_SQ_DETERMINANTS'
        WHEN sq_only_det_count > 0 AND calc_only_det_count = 0 THEN 'SQ_HAS_NO_CALC_MATCH'
        ELSE 'MIXED_DETERMINANT_MISMATCH'
    END
ORDER BY
    allocation_status;

-- 10d) Sample segments where calc lines exist outside billed-usage determinants
WITH completed_bseg AS (
    SELECT
        bseg.bseg_id,
        bseg.sa_id
    FROM cisadm.ci_bseg bseg
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
),
sq_det AS (
    SELECT
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~') AS uom_cd,
        NVL(TRIM(sq.tou_cd), '~') AS tou_cd,
        NVL(TRIM(sq.sqi_cd), '~') AS sqi_cd
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = sq.bseg_id
    GROUP BY
        sq.bseg_id,
        NVL(TRIM(sq.uom_cd), '~'),
        NVL(TRIM(sq.tou_cd), '~'),
        NVL(TRIM(sq.sqi_cd), '~')
),
calc_det AS (
    SELECT
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~') AS uom_cd,
        NVL(TRIM(ln.tou_cd), '~') AS tou_cd,
        NVL(TRIM(ln.sqi_cd), '~') AS sqi_cd,
        SUM(NVL(ln.calc_amt, 0)) AS total_calc_amt
    FROM cisadm.ci_bseg_calc_ln ln
    INNER JOIN completed_bseg cb
        ON cb.bseg_id = ln.bseg_id
    GROUP BY
        ln.bseg_id,
        NVL(TRIM(ln.uom_cd), '~'),
        NVL(TRIM(ln.tou_cd), '~'),
        NVL(TRIM(ln.sqi_cd), '~')
),
calc_only AS (
    SELECT
        calc.bseg_id,
        calc.uom_cd,
        calc.tou_cd,
        calc.sqi_cd,
        calc.total_calc_amt
    FROM calc_det calc
    LEFT JOIN sq_det sq
        ON sq.bseg_id = calc.bseg_id
       AND sq.uom_cd = calc.uom_cd
       AND sq.tou_cd = calc.tou_cd
       AND sq.sqi_cd = calc.sqi_cd
    WHERE sq.bseg_id IS NULL
)
SELECT *
FROM (
    SELECT
        sa.sa_type_cd,
        sa_type_l.descr AS sa_type_desc,
        co.bseg_id,
        co.uom_cd,
        co.tou_cd,
        co.sqi_cd,
        co.total_calc_amt
    FROM calc_only co
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = co.bseg_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = bseg.sa_id
    LEFT JOIN cisadm.ci_sa_type_l sa_type_l
        ON sa_type_l.sa_type_cd = sa.sa_type_cd
       AND sa_type_l.language_cd = 'ENG'
    ORDER BY
        co.total_calc_amt DESC,
        co.bseg_id
)
WHERE ROWNUM <= 100;
