-- Fast before/after validation for D1_MSRMT_RPT_CURR refresh-strategy changes.
--
-- Keeps only the highest-signal checks:
--   1. whole-table footprint
--   2. rolling 12-month source versus snapshot parity
--   3. duplicate natural-key check
--   4. current snapshot versus source total parity

PROMPT ============================================================================
PROMPT 08_fast_1. Whole-table footprint
PROMPT ============================================================================

SELECT
    COUNT(*) AS snapshot_rows,
    MIN(msrmt_dttm) AS min_msrmt_dttm,
    MAX(msrmt_dttm) AS max_msrmt_dttm,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm,
    SUM(msrmt_val) AS total_msrmt_val,
    SUM(reading_val) AS total_reading_val
FROM cisadm.d1_msrmt_rpt_curr;

PROMPT
PROMPT ============================================================================
PROMPT 08_fast_2. Rolling 12-month source versus snapshot parity
PROMPT ============================================================================

WITH source_monthly AS (
    SELECT
        TRUNC(msrmt.msrmt_dttm, 'MM') AS msrmt_month,
        COUNT(*) AS raw_rows,
        SUM(msrmt.msrmt_val) AS raw_msrmt_val,
        SUM(msrmt.reading_val) AS raw_reading_val
    FROM cisadm.d1_msrmt msrmt
    WHERE msrmt.msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(msrmt.msrmt_dttm, 'MM')
),
snapshot_monthly AS (
    SELECT
        TRUNC(msrmt_dttm, 'MM') AS msrmt_month,
        COUNT(*) AS snapshot_rows,
        SUM(msrmt_val) AS snapshot_msrmt_val,
        SUM(reading_val) AS snapshot_reading_val
    FROM cisadm.d1_msrmt_rpt_curr
    WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
    GROUP BY TRUNC(msrmt_dttm, 'MM')
)
SELECT
    COALESCE(s.msrmt_month, t.msrmt_month) AS msrmt_month,
    s.raw_rows,
    t.snapshot_rows,
    NVL(t.snapshot_rows, 0) - NVL(s.raw_rows, 0) AS snapshot_minus_raw_rows,
    s.raw_msrmt_val,
    t.snapshot_msrmt_val,
    NVL(t.snapshot_msrmt_val, 0) - NVL(s.raw_msrmt_val, 0) AS snapshot_minus_raw_msrmt_val,
    s.raw_reading_val,
    t.snapshot_reading_val,
    NVL(t.snapshot_reading_val, 0) - NVL(s.raw_reading_val, 0) AS snapshot_minus_raw_reading_val
FROM source_monthly s
FULL OUTER JOIN snapshot_monthly t
    ON t.msrmt_month = s.msrmt_month
ORDER BY msrmt_month;

PROMPT
PROMPT ============================================================================
PROMPT 08_fast_3. Duplicate natural-key check
PROMPT ============================================================================

SELECT
    measr_comp_id,
    msrmt_dttm,
    COUNT(*) AS row_count
FROM cisadm.d1_msrmt_rpt_curr
GROUP BY
    measr_comp_id,
    msrmt_dttm
HAVING COUNT(*) > 1;

PROMPT
PROMPT ============================================================================
PROMPT 08_fast_4. Current snapshot versus source total parity
PROMPT ============================================================================

SELECT
    (SELECT COUNT(*)
     FROM cisadm.d1_msrmt) AS source_rows,
    (SELECT COUNT(*)
     FROM cisadm.d1_msrmt_rpt_curr) AS snapshot_rows,
    (SELECT SUM(msrmt.msrmt_val)
     FROM cisadm.d1_msrmt msrmt) AS source_msrmt_val,
    (SELECT SUM(msrmt_val)
     FROM cisadm.d1_msrmt_rpt_curr) AS snapshot_msrmt_val,
    (SELECT SUM(msrmt.reading_val)
     FROM cisadm.d1_msrmt msrmt) AS source_reading_val,
    (SELECT SUM(reading_val)
     FROM cisadm.d1_msrmt_rpt_curr) AS snapshot_reading_val
FROM dual;
