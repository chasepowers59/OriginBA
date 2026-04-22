-- Before/after validation for FT_GL_DISTRIBUTION_RPT_CURR refresh-strategy changes.
--
-- Recommended use:
--   1. Run and save output before any FT-GL procedure change.
--   2. Deploy the candidate procedure.
--   3. Run one manual refresh.
--   4. Run this script again and compare results.

PROMPT ============================================================================
PROMPT 11a. Whole-table footprint
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
PROMPT 11b. Monthly snapshot counts and amounts by accounting month
PROMPT ============================================================================

SELECT
    TRUNC(accounting_dt, 'MM') AS accounting_month,
    COUNT(*) AS snapshot_rows,
    ROUND(SUM(gl_amount), 2) AS snapshot_gl_amount,
    SUM(statistic_amount) AS snapshot_statistic_amount
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE accounting_dt IS NOT NULL
GROUP BY TRUNC(accounting_dt, 'MM')
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 11c. Rolling 12-month source versus snapshot parity
PROMPT ============================================================================

WITH source_monthly AS (
    SELECT
        TRUNC(ft.accounting_dt, 'MM') AS accounting_month,
        COUNT(*) AS raw_rows,
        ROUND(SUM(gl.amount), 2) AS raw_gl_amount,
        SUM(gl.statistic_amount) AS raw_statistic_amount
    FROM cisadm.ci_ft_gl gl
    JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(ft.accounting_dt, 'MM')
),
snapshot_monthly AS (
    SELECT
        TRUNC(accounting_dt, 'MM') AS accounting_month,
        COUNT(*) AS snapshot_rows,
        ROUND(SUM(gl_amount), 2) AS snapshot_gl_amount,
        SUM(statistic_amount) AS snapshot_statistic_amount
    FROM cisadm.ft_gl_distribution_rpt_curr
    WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(accounting_dt, 'MM')
)
SELECT
    COALESCE(s.accounting_month, t.accounting_month) AS accounting_month,
    s.raw_rows,
    t.snapshot_rows,
    NVL(t.snapshot_rows, 0) - NVL(s.raw_rows, 0) AS snapshot_minus_raw_rows,
    s.raw_gl_amount,
    t.snapshot_gl_amount,
    ROUND(NVL(t.snapshot_gl_amount, 0) - NVL(s.raw_gl_amount, 0), 2) AS snapshot_minus_raw_gl_amount,
    s.raw_statistic_amount,
    t.snapshot_statistic_amount,
    NVL(t.snapshot_statistic_amount, 0) - NVL(s.raw_statistic_amount, 0) AS snapshot_minus_raw_statistic_amount
FROM source_monthly s
FULL OUTER JOIN snapshot_monthly t
    ON t.accounting_month = s.accounting_month
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 11d. Older-than-window history retention
PROMPT ============================================================================

SELECT
    TRUNC(accounting_dt, 'MM') AS accounting_month,
    COUNT(*) AS snapshot_rows_older_than_window,
    ROUND(SUM(gl_amount), 2) AS snapshot_gl_amount_older_than_window,
    SUM(statistic_amount) AS snapshot_statistic_amount_older_than_window
FROM cisadm.ft_gl_distribution_rpt_curr
WHERE accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY TRUNC(accounting_dt, 'MM')
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 11e. Duplicate natural-key check
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
PROMPT 11f. Current snapshot versus source total parity
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
