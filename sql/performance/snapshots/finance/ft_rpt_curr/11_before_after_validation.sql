-- Before/after validation for FT_RPT_CURR refresh-strategy changes.

PROMPT ============================================================================
PROMPT 11a. Whole-table footprint
PROMPT ============================================================================

SELECT
    COUNT(*) AS snapshot_rows,
    MIN(accounting_dt) AS min_accounting_dt,
    MAX(accounting_dt) AS max_accounting_dt,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm,
    ROUND(SUM(cur_amt), 2) AS total_cur_amt,
    ROUND(SUM(tot_amt), 2) AS total_tot_amt
FROM cisadm.ft_rpt_curr;

PROMPT
PROMPT ============================================================================
PROMPT 11b. Monthly snapshot counts and amounts by accounting month
PROMPT ============================================================================

SELECT
    TRUNC(accounting_dt, 'MM') AS accounting_month,
    COUNT(*) AS snapshot_rows,
    ROUND(SUM(cur_amt), 2) AS snapshot_cur_amt,
    ROUND(SUM(tot_amt), 2) AS snapshot_tot_amt
FROM cisadm.ft_rpt_curr
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
        ROUND(SUM(ft.cur_amt), 2) AS raw_cur_amt,
        ROUND(SUM(ft.tot_amt), 2) AS raw_tot_amt
    FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N'
      AND ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(ft.accounting_dt, 'MM')
),
snapshot_monthly AS (
    SELECT
        TRUNC(accounting_dt, 'MM') AS accounting_month,
        COUNT(*) AS snapshot_rows,
        ROUND(SUM(cur_amt), 2) AS snapshot_cur_amt,
        ROUND(SUM(tot_amt), 2) AS snapshot_tot_amt
    FROM cisadm.ft_rpt_curr
    WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(accounting_dt, 'MM')
)
SELECT
    COALESCE(s.accounting_month, t.accounting_month) AS accounting_month,
    s.raw_rows,
    t.snapshot_rows,
    NVL(t.snapshot_rows, 0) - NVL(s.raw_rows, 0) AS snapshot_minus_raw_rows,
    s.raw_cur_amt,
    t.snapshot_cur_amt,
    ROUND(NVL(t.snapshot_cur_amt, 0) - NVL(s.raw_cur_amt, 0), 2) AS snapshot_minus_raw_cur_amt,
    s.raw_tot_amt,
    t.snapshot_tot_amt,
    ROUND(NVL(t.snapshot_tot_amt, 0) - NVL(s.raw_tot_amt, 0), 2) AS snapshot_minus_raw_tot_amt
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
    ROUND(SUM(cur_amt), 2) AS snapshot_cur_amt_older_than_window,
    ROUND(SUM(tot_amt), 2) AS snapshot_tot_amt_older_than_window
FROM cisadm.ft_rpt_curr
WHERE accounting_dt < ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY TRUNC(accounting_dt, 'MM')
ORDER BY accounting_month;

PROMPT
PROMPT ============================================================================
PROMPT 11e. Duplicate natural-key check
PROMPT ============================================================================

SELECT
    ft_id,
    COUNT(*) AS row_count
FROM cisadm.ft_rpt_curr
GROUP BY ft_id
HAVING COUNT(*) > 1;

PROMPT
PROMPT ============================================================================
PROMPT 11f. Current snapshot versus source total parity
PROMPT ============================================================================

SELECT
    (SELECT COUNT(*)
     FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N') AS source_rows,
    (SELECT COUNT(*)
     FROM cisadm.ft_rpt_curr) AS snapshot_rows,
    (SELECT ROUND(SUM(ft.cur_amt), 2)
     FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N') AS source_cur_amt,
    (SELECT ROUND(SUM(cur_amt), 2)
     FROM cisadm.ft_rpt_curr) AS snapshot_cur_amt,
    (SELECT ROUND(SUM(ft.tot_amt), 2)
     FROM cisadm.ci_ft ft
    WHERE ft.redundant_sw = 'N') AS source_tot_amt,
    (SELECT ROUND(SUM(tot_amt), 2)
     FROM cisadm.ft_rpt_curr) AS snapshot_tot_amt
FROM dual;
