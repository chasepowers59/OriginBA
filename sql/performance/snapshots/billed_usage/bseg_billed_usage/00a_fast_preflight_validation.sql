-- Purpose:
--   Fast preflight checks for the legacy billed-usage domain.
--
-- Goal:
--   Prove where CI_BSEG_SQ, CI_BSEG_READ, and CI_BSEG_CALC multiply CI_BSEG
--   and determine whether the reporting truth should be BSEG grain or
--   BSEG_SQ grain.

-- 1) Completed-bill baseline
SELECT COUNT(*) AS completed_bill_rows
FROM cisadm.ci_bill
WHERE bill_stat_flg = 'C ';

SELECT COUNT(*) AS completed_bseg_rows
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

SELECT
    COUNT(DISTINCT bseg.bseg_id) AS distinct_completed_bseg_ids
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

-- 2) BSEG child-row coverage by table
SELECT
    COUNT(*) AS completed_bseg_rows,
    SUM(CASE WHEN sq.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS bseg_with_sq,
    SUM(CASE WHEN rd.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS bseg_with_read,
    SUM(CASE WHEN calc.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS bseg_with_calc
FROM cisadm.ci_bseg bseg
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
LEFT JOIN (
    SELECT DISTINCT bseg_id
    FROM cisadm.ci_bseg_sq
) sq
    ON sq.bseg_id = bseg.bseg_id
LEFT JOIN (
    SELECT DISTINCT bseg_id
    FROM cisadm.ci_bseg_read
) rd
    ON rd.bseg_id = bseg.bseg_id
LEFT JOIN (
    SELECT DISTINCT bseg_id
    FROM cisadm.ci_bseg_calc
) calc
    ON calc.bseg_id = bseg.bseg_id
WHERE bill.bill_stat_flg = 'C ';

-- 3) How many SQ lines exist per completed BSEG
SELECT
    COUNT(*) AS bseg_with_sq_rows,
    SUM(sq_line_count) AS total_sq_lines,
    AVG(sq_line_count) AS avg_sq_lines_per_bseg,
    MAX(sq_line_count) AS max_sq_lines_per_bseg
FROM (
    SELECT
        sq.bseg_id,
        COUNT(*) AS sq_line_count
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id
);

SELECT *
FROM (
    SELECT
        sq.bseg_id,
        COUNT(*) AS sq_line_count
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC, sq.bseg_id
)
WHERE ROWNUM <= 50;

-- 4) Distinct determinant combinations per BSEG_SQ
SELECT
    COUNT(*) AS sq_rows,
    COUNT(DISTINCT sq.bseg_id) AS bseg_count,
    COUNT(DISTINCT sq.bseg_id || ':' || NVL(sq.uom_cd, '~') || ':' || NVL(sq.tou_cd, '~') || ':' || NVL(sq.sqi_cd, '~')) AS distinct_bseg_sq_keys
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

-- 5) How many read rows exist per completed BSEG
SELECT
    COUNT(*) AS bseg_with_read_rows,
    SUM(read_line_count) AS total_read_lines,
    AVG(read_line_count) AS avg_read_lines_per_bseg,
    MAX(read_line_count) AS max_read_lines_per_bseg
FROM (
    SELECT
        rd.bseg_id,
        COUNT(*) AS read_line_count
    FROM cisadm.ci_bseg_read rd
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = rd.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        rd.bseg_id
);

-- 6) How many calc headers exist per completed BSEG
SELECT
    COUNT(*) AS bseg_with_calc_rows,
    SUM(calc_line_count) AS total_calc_headers,
    AVG(calc_line_count) AS avg_calc_headers_per_bseg,
    MAX(calc_line_count) AS max_calc_headers_per_bseg
FROM (
    SELECT
        calc.bseg_id,
        COUNT(*) AS calc_line_count
    FROM cisadm.ci_bseg_calc calc
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = calc.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        calc.bseg_id
);

-- 7) Multiplication proof: raw legacy join shape
SELECT COUNT(*) AS legacy_join_row_count
FROM cisadm.ci_bill bill
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bill_id = bill.bill_id
INNER JOIN cisadm.ci_bseg_read rd
    ON rd.bseg_id = bseg.bseg_id
INNER JOIN cisadm.ci_bseg_sq sq
    ON sq.bseg_id = bseg.bseg_id
INNER JOIN cisadm.ci_bseg_calc calc
    ON calc.bseg_id = bseg.bseg_id
WHERE bill.bill_stat_flg = 'C ';

SELECT COUNT(*) AS legacy_distinct_bseg_count
FROM (
    SELECT
        bseg.bseg_id
    FROM cisadm.ci_bill bill
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bill_id = bill.bill_id
    INNER JOIN cisadm.ci_bseg_read rd
        ON rd.bseg_id = bseg.bseg_id
    INNER JOIN cisadm.ci_bseg_sq sq
        ON sq.bseg_id = bseg.bseg_id
    INNER JOIN cisadm.ci_bseg_calc calc
        ON calc.bseg_id = bseg.bseg_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        bseg.bseg_id
);

-- 8) Duplication proof on billed usage
SELECT
    SUM(sq.bill_sq) AS direct_bill_sq_total
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
WHERE bill.bill_stat_flg = 'C ';

SELECT
    SUM(sq.bill_sq) AS duplicated_bill_sq_total_after_legacy_join
FROM cisadm.ci_bill bill
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bill_id = bill.bill_id
INNER JOIN cisadm.ci_bseg_read rd
    ON rd.bseg_id = bseg.bseg_id
INNER JOIN cisadm.ci_bseg_sq sq
    ON sq.bseg_id = bseg.bseg_id
INNER JOIN cisadm.ci_bseg_calc calc
    ON calc.bseg_id = bseg.bseg_id
WHERE bill.bill_stat_flg = 'C ';

-- 9) Trusted BSEG-grain usage rollup from CI_BSEG_SQ alone
SELECT
    COUNT(*) AS bseg_count,
    SUM(total_bill_sq) AS total_bill_sq,
    SUM(total_init_sq) AS total_init_sq
FROM (
    SELECT
        sq.bseg_id,
        SUM(NVL(sq.bill_sq, 0)) AS total_bill_sq,
        SUM(NVL(sq.init_sq, 0)) AS total_init_sq
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id
);

-- 10) Profile how many determinant combinations exist per BSEG
SELECT
    determinant_count,
    COUNT(*) AS bseg_count
FROM (
    SELECT
        sq.bseg_id,
        COUNT(*) AS determinant_count
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.bseg_id
)
GROUP BY
    determinant_count
ORDER BY
    determinant_count;

-- 11) Preview billed usage by determinant
SELECT *
FROM (
    SELECT
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd,
        COUNT(*) AS bseg_sq_rows,
        COUNT(DISTINCT sq.bseg_id) AS bseg_count,
        SUM(sq.bill_sq) AS total_bill_sq
    FROM cisadm.ci_bseg_sq sq
    INNER JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = sq.bseg_id
    INNER JOIN cisadm.ci_bill bill
        ON bill.bill_id = bseg.bill_id
    WHERE bill.bill_stat_flg = 'C '
    GROUP BY
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
    ORDER BY
        SUM(sq.bill_sq) DESC,
        sq.uom_cd,
        sq.tou_cd,
        sq.sqi_cd
)
WHERE ROWNUM <= 100;

-- 12) Lookup coverage on BSEG_SQ determinants
SELECT
    COUNT(*) AS total_sq_rows,
    SUM(CASE WHEN uom_l.descr IS NULL AND sq.uom_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_uom_desc,
    SUM(CASE WHEN tou_l.descr IS NULL AND sq.tou_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_tou_desc,
    SUM(CASE WHEN sqi_l.descr IS NULL AND sq.sqi_cd IS NOT NULL THEN 1 ELSE 0 END) AS missing_sqi_desc
FROM cisadm.ci_bseg_sq sq
INNER JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = sq.bseg_id
INNER JOIN cisadm.ci_bill bill
    ON bill.bill_id = bseg.bill_id
LEFT JOIN cisadm.ci_uom_l uom_l
    ON uom_l.uom_cd = sq.uom_cd
   AND uom_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_tou_l tou_l
    ON tou_l.tou_cd = sq.tou_cd
   AND tou_l.language_cd = 'ENG'
LEFT JOIN cisadm.ci_sqi_l sqi_l
    ON sqi_l.sqi_cd = sq.sqi_cd
   AND sqi_l.language_cd = 'ENG'
WHERE bill.bill_stat_flg = 'C ';
