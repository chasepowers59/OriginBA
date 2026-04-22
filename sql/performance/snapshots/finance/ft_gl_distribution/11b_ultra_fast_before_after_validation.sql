-- Ultra-fast before/after validation for FT_GL_DISTRIBUTION_RPT_CURR.
--
-- Use this when:
--   - you need the fastest possible baseline before a procedure cutover
--   - the monthly rolling parity checks are too slow for quick iteration
--
-- Keeps only:
--   1. whole-table footprint
--   2. duplicate natural-key check
--   3. total source versus snapshot parity

PROMPT ============================================================================
PROMPT 11b_ultra_fast_1. Whole-table footprint
PROMPT ============================================================================

SELECT
    COUNT(*) AS snapshot_rows,
    COUNT(DISTINCT ft_id) AS distinct_ft_id,
    MIN(accounting_dt) AS min_accounting_dt,
    MAX(accounting_dt) AS max_accounting_dt,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm,
    ROUND(SUM(gl_amount), 2) AS total_gl_amount,
    SUM(statistic_amount) AS total_statistic_amount
FROM cisadm.ft_gl_distribution_rpt_curr;

PROMPT
PROMPT ============================================================================
PROMPT 11b_ultra_fast_2. Duplicate natural-key check
PROMPT ============================================================================

SELECT
    ft_id,
    gl_seq_nbr,
    COUNT(*) AS row_count
FROM cisadm.ft_gl_distribution_rpt_curr
GROUP BY
    ft_id,
    gl_seq_nbr
HAVING COUNT(*) > 1;

PROMPT
PROMPT ============================================================================
PROMPT 11b_ultra_fast_3. Current snapshot versus source total parity
PROMPT ============================================================================

SELECT
    (SELECT COUNT(*)
     FROM cisadm.ci_ft_gl gl
     JOIN cisadm.ci_ft ft
       ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N') AS source_rows,
    (SELECT COUNT(*)
     FROM cisadm.ft_gl_distribution_rpt_curr) AS snapshot_rows,
    (SELECT ROUND(SUM(gl.amount), 2)
     FROM cisadm.ci_ft_gl gl
     JOIN cisadm.ci_ft ft
       ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N') AS source_gl_amount,
    (SELECT ROUND(SUM(gl_amount), 2)
     FROM cisadm.ft_gl_distribution_rpt_curr) AS snapshot_gl_amount,
    (SELECT SUM(gl.statistic_amount)
     FROM cisadm.ci_ft_gl gl
     JOIN cisadm.ci_ft ft
       ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N') AS source_statistic_amount,
    (SELECT SUM(statistic_amount)
     FROM cisadm.ft_gl_distribution_rpt_curr) AS snapshot_statistic_amount
FROM dual;
