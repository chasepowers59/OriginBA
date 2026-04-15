-- Purpose:
--   Fast preflight checks for the FT / GL distribution snapshot.
--
-- Use this first:
--   - to confirm the snapshot grain should be FT_GL line
--   - to prove FT amounts would duplicate if summarized at GL-line joins
--   - to validate child-table coverage by FT type
--   - to preview the actual GL-account-by-FT-type output shape

-- 1) Baseline counts
SELECT COUNT(*) AS source_ft_rows
FROM cisadm.ci_ft
WHERE redundant_sw = 'N';

SELECT COUNT(*) AS source_ft_gl_rows
FROM cisadm.ci_ft_gl;

SELECT COUNT(DISTINCT ft_id) AS ft_ids_present_in_ft_gl
FROM cisadm.ci_ft_gl;

-- 2) FT type distribution at FT grain
SELECT
    ft_type_flg,
    COUNT(*) AS ft_row_count,
    SUM(cur_amt) AS ft_cur_amt,
    SUM(tot_amt) AS ft_tot_amt
FROM cisadm.ci_ft
WHERE redundant_sw = 'N'
GROUP BY
    ft_type_flg
ORDER BY
    ft_type_flg;

-- 3) FT type distribution with GL coverage
SELECT
    ft.ft_type_flg,
    COUNT(*) AS ft_row_count,
    SUM(CASE WHEN gl.ft_id IS NOT NULL THEN 1 ELSE 0 END) AS ft_rows_with_gl,
    SUM(CASE WHEN gl.ft_id IS NULL THEN 1 ELSE 0 END) AS ft_rows_without_gl,
    SUM(NVL(gl.gl_line_count, 0)) AS total_gl_lines,
    AVG(NVL(gl.gl_line_count, 0)) AS avg_gl_lines_per_ft
FROM cisadm.ci_ft ft
LEFT JOIN (
    SELECT
        ft_id,
        COUNT(*) AS gl_line_count
    FROM cisadm.ci_ft_gl
    GROUP BY
        ft_id
) gl
    ON gl.ft_id = ft.ft_id
WHERE ft.redundant_sw = 'N'
GROUP BY
    ft.ft_type_flg
ORDER BY
    ft.ft_type_flg;

-- 4) Proof that FT-header amounts duplicate when repeated across GL lines
SELECT
    SUM(ft.cur_amt) AS ft_cur_amt_for_fts_with_gl
FROM cisadm.ci_ft ft
WHERE ft.redundant_sw = 'N'
  AND EXISTS (
        SELECT 1
        FROM cisadm.ci_ft_gl gl
        WHERE gl.ft_id = ft.ft_id
    );

SELECT
    SUM(ft.cur_amt) AS duplicated_ft_cur_amt_after_gl_join
FROM cisadm.ci_ft ft
INNER JOIN cisadm.ci_ft_gl gl
    ON gl.ft_id = ft.ft_id
WHERE ft.redundant_sw = 'N';

-- 5) Actual GL amount baseline
SELECT
    SUM(gl.amount) AS total_gl_amount,
    SUM(gl.statistic_amount) AS total_statistic_amount
FROM cisadm.ci_ft_gl gl;

-- 6) FT-type child coverage using corrected type-conditional joins
SELECT
    ft.ft_type_flg,
    COUNT(*) AS ft_rows,
    SUM(CASE WHEN ft.ft_type_flg IN ('BS', 'BX') AND bseg.bseg_id IS NULL THEN 1 ELSE 0 END) AS missing_bseg,
    SUM(CASE WHEN ft.ft_type_flg IN ('AD', 'AX') AND adj.adj_id IS NULL THEN 1 ELSE 0 END) AS missing_adj,
    SUM(CASE WHEN ft.ft_type_flg IN ('PS', 'PX') AND pay_seg.pay_seg_id IS NULL THEN 1 ELSE 0 END) AS missing_pay_seg
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_bseg bseg
    ON bseg.bseg_id = ft.sibling_id
   AND bseg.bill_id = ft.bill_id
   AND ft.ft_type_flg IN ('BS', 'BX')
LEFT JOIN cisadm.ci_adj adj
    ON adj.adj_id = ft.sibling_id
   AND ft.ft_type_flg IN ('AD', 'AX')
LEFT JOIN cisadm.ci_pay_seg pay_seg
    ON pay_seg.pay_seg_id = ft.sibling_id
   AND pay_seg.pay_id = ft.parent_id
   AND ft.ft_type_flg IN ('PS', 'PX')
WHERE ft.redundant_sw = 'N'
GROUP BY
    ft.ft_type_flg
ORDER BY
    ft.ft_type_flg;

-- 7) Legacy adjustment join vs corrected adjustment join
SELECT
    COUNT(*) AS adj_ft_rows,
    SUM(CASE WHEN legacy_adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS legacy_adj_join_hits,
    SUM(CASE WHEN corrected_adj.adj_id IS NOT NULL THEN 1 ELSE 0 END) AS corrected_adj_join_hits
FROM cisadm.ci_ft ft
LEFT JOIN cisadm.ci_adj legacy_adj
    ON legacy_adj.adj_id = ft.sibling_id
   AND legacy_adj.adj_type_cd = ft.parent_id
LEFT JOIN cisadm.ci_adj corrected_adj
    ON corrected_adj.adj_id = ft.sibling_id
WHERE ft.redundant_sw = 'N'
  AND ft.ft_type_flg IN ('AD', 'AX');

-- 8) GL account by FT type breakdown preview
SELECT *
FROM (
    SELECT
        gl.gl_acct,
        gl.dst_id,
        ft.ft_type_flg,
        COUNT(*) AS gl_line_count,
        COUNT(DISTINCT ft.ft_id) AS ft_count,
        SUM(gl.amount) AS gl_amount
    FROM cisadm.ci_ft_gl gl
    INNER JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
    GROUP BY
        gl.gl_acct,
        gl.dst_id,
        ft.ft_type_flg
    ORDER BY
        SUM(gl.amount) DESC,
        gl.gl_acct,
        gl.dst_id,
        ft.ft_type_flg
)
WHERE ROWNUM <= 100;

-- 9) Distribution-code lookup coverage on real GL rows
SELECT
    COUNT(*) AS total_gl_rows,
    SUM(CASE WHEN dst_l.descr IS NULL AND gl.dst_id IS NOT NULL THEN 1 ELSE 0 END) AS missing_dst_descr
FROM cisadm.ci_ft_gl gl
LEFT JOIN cisadm.ci_dst_code_l dst_l
    ON dst_l.dst_id = gl.dst_id
   AND dst_l.language_cd = 'ENG';

-- 10) Trend-area legacy join anomaly check
SELECT
    COUNT(*) AS premise_rows_with_trend_area_cd,
    SUM(CASE WHEN trend_by_code.trend_area_cd IS NOT NULL THEN 1 ELSE 0 END) AS matches_on_code,
    SUM(CASE WHEN trend_by_descr.trend_area_cd IS NOT NULL THEN 1 ELSE 0 END) AS matches_on_legacy_descr_join
FROM cisadm.ci_prem prem
LEFT JOIN cisadm.ci_trend_area_l trend_by_code
    ON trend_by_code.trend_area_cd = prem.trend_area_cd
   AND trend_by_code.language_cd = 'ENG'
LEFT JOIN cisadm.ci_trend_area_l trend_by_descr
    ON trend_by_descr.descr = prem.trend_area_cd
   AND trend_by_descr.language_cd = 'ENG'
WHERE prem.trend_area_cd IS NOT NULL;
