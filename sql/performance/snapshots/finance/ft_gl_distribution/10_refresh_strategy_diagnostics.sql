-- Refresh strategy diagnostics for CISADM.FT_GL_DISTRIBUTION_RPT_CURR
--
-- Purpose:
--   Measure whether a rolling 6-month or 12-month refresh is a safe next step
--   for FT_GL_DISTRIBUTION_RPT_CURR, or whether the object should remain a
--   full rebuild and be optimized in-place.
--
-- Key questions answered:
--   1. How much of the FT-GL population sits in the last 6 / 12 / 24 months?
--   2. How much of the current runtime is spent rebuilding older history?
--   3. Are newly created FT / FT-GL rows frequently back-posting into older
--      accounting periods?
--   4. Would a rolling window keep most of the active volume or introduce risk?
--
-- Recommended use:
--   Run all sections and save the output before changing the FT-GL refresh
--   procedure from full rebuild to any rolling-window model.

PROMPT ============================================================================
PROMPT 10a. Source and snapshot footprint
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        ft.accounting_dt,
        ft.cre_dttm,
        gl.amount AS gl_amount,
        gl.statistic_amount
    FROM cisadm.ci_ft_gl gl
    JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
)
SELECT
    (SELECT COUNT(*) FROM source_base) AS source_rows,
    (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr) AS snapshot_rows,
    (SELECT MIN(accounting_dt) FROM source_base) AS min_accounting_dt,
    (SELECT MAX(accounting_dt) FROM source_base) AS max_accounting_dt,
    (SELECT MIN(cre_dttm) FROM source_base) AS min_ft_cre_dttm,
    (SELECT MAX(cre_dttm) FROM source_base) AS max_ft_cre_dttm,
    (SELECT MIN(load_dttm) FROM cisadm.ft_gl_distribution_rpt_curr) AS min_load_dttm,
    (SELECT MAX(load_dttm) FROM cisadm.ft_gl_distribution_rpt_curr) AS max_load_dttm
FROM dual;

PROMPT
PROMPT ============================================================================
PROMPT 10b. Monthly accounting-date distribution
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        TRUNC(ft.accounting_dt, 'MM') AS accounting_month,
        gl.amount AS gl_amount,
        gl.statistic_amount
    FROM cisadm.ci_ft_gl gl
    JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
)
SELECT
    accounting_month,
    COUNT(*) AS gl_rows,
    ROUND(SUM(gl_amount), 2) AS gl_amount,
    SUM(statistic_amount) AS statistic_amount
FROM source_base
GROUP BY accounting_month
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 10c. Rolling window share of current source population
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        ft.accounting_dt,
        gl.amount AS gl_amount,
        gl.statistic_amount
    FROM cisadm.ci_ft_gl gl
    JOIN cisadm.ci_ft ft
        ON ft.ft_id = gl.ft_id
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
),
windows AS (
    SELECT 'LAST_6_MONTHS' AS window_name,
           ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) AS window_start
    FROM dual
    UNION ALL
    SELECT 'LAST_12_MONTHS',
           ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    FROM dual
    UNION ALL
    SELECT 'LAST_24_MONTHS',
           ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24)
    FROM dual
)
SELECT
    w.window_name,
    w.window_start,
    COUNT(CASE WHEN s.accounting_dt >= w.window_start THEN 1 END) AS rows_in_window,
    COUNT(CASE WHEN s.accounting_dt < w.window_start THEN 1 END) AS rows_older_than_window,
    ROUND(
        100 * COUNT(CASE WHEN s.accounting_dt >= w.window_start THEN 1 END) / COUNT(*),
        2
    ) AS pct_rows_in_window,
    ROUND(SUM(CASE WHEN s.accounting_dt >= w.window_start THEN s.gl_amount ELSE 0 END), 2) AS gl_amount_in_window,
    ROUND(SUM(CASE WHEN s.accounting_dt < w.window_start THEN s.gl_amount ELSE 0 END), 2) AS gl_amount_older_than_window,
    SUM(CASE WHEN s.accounting_dt >= w.window_start THEN s.statistic_amount ELSE 0 END) AS statistic_amount_in_window,
    SUM(CASE WHEN s.accounting_dt < w.window_start THEN s.statistic_amount ELSE 0 END) AS statistic_amount_older_than_window
FROM windows w
CROSS JOIN source_base s
GROUP BY
    w.window_name,
    w.window_start
ORDER BY w.window_start;

PROMPT
PROMPT ============================================================================
PROMPT 10d. Recent FT creation landing in older accounting periods
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        ft.ft_id,
        ft.accounting_dt,
        ft.cre_dttm
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
      AND ft.cre_dttm IS NOT NULL
),
windows AS (
    SELECT 'CREATED_LAST_30_DAYS' AS created_window_name,
           SYSDATE - 30 AS created_window_start,
           1 AS sort_order
    FROM dual
    UNION ALL
    SELECT 'CREATED_LAST_90_DAYS',
           SYSDATE - 90,
           2
    FROM dual
    UNION ALL
    SELECT 'CREATED_LAST_180_DAYS',
           SYSDATE - 180,
           3
    FROM dual
)
SELECT
    w.created_window_name,
    COUNT(*) AS ft_rows_created_in_window,
    COUNT(CASE WHEN s.accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) THEN 1 END) AS acct_older_than_6_months,
    COUNT(CASE WHEN s.accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) THEN 1 END) AS acct_older_than_12_months,
    COUNT(CASE WHEN s.accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24) THEN 1 END) AS acct_older_than_24_months
FROM windows w
JOIN source_base s
    ON s.cre_dttm >= w.created_window_start
GROUP BY
    w.created_window_name,
    w.sort_order
ORDER BY w.sort_order;

PROMPT
PROMPT ============================================================================
PROMPT 10e. Accounting-date versus create-date lag profile
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        ft.ft_id,
        ft.accounting_dt,
        ft.cre_dttm,
        TRUNC(ft.cre_dttm) - TRUNC(ft.accounting_dt) AS lag_days
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
      AND ft.cre_dttm IS NOT NULL
),
lag_profile AS (
    SELECT
        CASE
            WHEN lag_days < 0 THEN 'CREATED_BEFORE_ACCOUNTING_DT'
            WHEN lag_days BETWEEN 0 AND 7 THEN '0_TO_7_DAYS'
            WHEN lag_days BETWEEN 8 AND 30 THEN '8_TO_30_DAYS'
            WHEN lag_days BETWEEN 31 AND 90 THEN '31_TO_90_DAYS'
            WHEN lag_days BETWEEN 91 AND 180 THEN '91_TO_180_DAYS'
            WHEN lag_days BETWEEN 181 AND 365 THEN '181_TO_365_DAYS'
            ELSE 'OVER_365_DAYS'
        END AS lag_bucket,
        CASE
            WHEN lag_days < 0 THEN 1
            WHEN lag_days BETWEEN 0 AND 7 THEN 2
            WHEN lag_days BETWEEN 8 AND 30 THEN 3
            WHEN lag_days BETWEEN 31 AND 90 THEN 4
            WHEN lag_days BETWEEN 91 AND 180 THEN 5
            WHEN lag_days BETWEEN 181 AND 365 THEN 6
            ELSE 7
        END AS sort_order
    FROM source_base
)
SELECT
    lag_bucket,
    COUNT(*) AS ft_rows
FROM lag_profile
GROUP BY
    lag_bucket,
    sort_order
ORDER BY sort_order;

PROMPT
PROMPT ============================================================================
PROMPT 10f. Recent creations into old accounting months by month
PROMPT ============================================================================

WITH source_base AS (
    SELECT
        TRUNC(ft.accounting_dt, 'MM') AS accounting_month,
        ft.cre_dttm
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
      AND ft.cre_dttm >= SYSDATE - 180
)
SELECT
    accounting_month,
    COUNT(*) AS ft_rows_created_last_180_days
FROM source_base
GROUP BY accounting_month
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 10g. Sample oldest accounting periods still receiving recent creates
PROMPT ============================================================================

SELECT *
FROM (
    SELECT
        ft.ft_id,
        ft.accounting_dt,
        ft.cre_dttm,
        TRUNC(ft.cre_dttm) - TRUNC(ft.accounting_dt) AS lag_days,
        ft.ft_type_flg,
        ft.sa_id,
        ft.bill_id,
        ft.parent_id,
        ft.sibling_id
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt IS NOT NULL
      AND ft.cre_dttm IS NOT NULL
      AND ft.cre_dttm >= SYSDATE - 180
      AND ft.accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    ORDER BY ft.accounting_dt, ft.cre_dttm DESC
)
WHERE ROWNUM <= 100;
