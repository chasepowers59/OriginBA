-- Intensive QA pack for CISADM.D1_USAGE_RPT_CURR
-- Read-only. Use after refresh to prove usage-header parity,
-- optional billing-bridge behavior, and end-user readiness.

-- 6a) Source vs snapshot baseline
SELECT
    (SELECT COUNT(*)
     FROM cisadm.d1_usage u
     WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL) AS source_usage_count,
    (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr) AS snapshot_usage_count,
    (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr) -
    (SELECT COUNT(*)
     FROM cisadm.d1_usage u
     WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL) AS snapshot_minus_source
FROM dual;

-- 6b) Anti-join counts
SELECT COUNT(*) AS source_rows_missing_in_snapshot
FROM (
    SELECT u.d1_usage_id
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
    MINUS
    SELECT s.d1_usage_id
    FROM cisadm.d1_usage_rpt_curr s
);

SELECT COUNT(*) AS snapshot_rows_not_in_source
FROM (
    SELECT s.d1_usage_id
    FROM cisadm.d1_usage_rpt_curr s
    MINUS
    SELECT u.d1_usage_id
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
);

-- 6c) Monthly parity by best available usage timestamp
WITH src AS (
    SELECT
        TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM') AS usage_month,
        COUNT(*) AS src_row_count
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
    GROUP BY TRUNC(NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)), 'MM')
),
snap AS (
    SELECT
        TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM') AS usage_month,
        COUNT(*) AS snap_row_count
    FROM cisadm.d1_usage_rpt_curr s
    GROUP BY TRUNC(NVL(s.start_dttm, NVL(s.usage_cre_dttm, s.status_upd_dttm)), 'MM')
)
SELECT
    NVL(src.usage_month, snap.usage_month) AS usage_month,
    NVL(src.src_row_count, 0) AS src_row_count,
    NVL(snap.snap_row_count, 0) AS snap_row_count,
    NVL(snap.snap_row_count, 0) - NVL(src.src_row_count, 0) AS row_count_diff
FROM src
FULL OUTER JOIN snap
    ON snap.usage_month = src.usage_month
ORDER BY usage_month;

-- 6d) Optional billing-bridge and business-context coverage
WITH src AS (
    SELECT
        COUNT(*) AS src_rows,
        SUM(CASE WHEN cu.usage_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_c1_usage,
        SUM(CASE WHEN bseg.bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_bseg,
        SUM(CASE WHEN sa.sa_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_sa,
        SUM(CASE WHEN acct.acct_id IS NOT NULL THEN 1 ELSE 0 END) AS src_rows_with_acct
    FROM cisadm.d1_usage u
    LEFT JOIN cisadm.c1_usage cu
        ON cu.usage_id = u.usg_ext_id
       AND cu.bo_status_cd = 'BD-PROC'
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = cu.bseg_id
    LEFT JOIN cisadm.ci_sa sa
        ON sa.sa_id = COALESCE(cu.sa_id, bseg.sa_id)
    LEFT JOIN cisadm.ci_acct acct
        ON acct.acct_id = sa.acct_id
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
),
snap AS (
    SELECT
        COUNT(*) AS snap_rows,
        SUM(CASE WHEN c1_usage_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_c1_usage,
        SUM(CASE WHEN c1_bseg_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_bseg,
        SUM(CASE WHEN sa_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_sa,
        SUM(CASE WHEN acct_id IS NOT NULL THEN 1 ELSE 0 END) AS snap_rows_with_acct
    FROM cisadm.d1_usage_rpt_curr
)
SELECT
    src.src_rows,
    snap.snap_rows,
    snap.snap_rows - src.src_rows AS row_diff,
    src.src_rows_with_c1_usage,
    snap.snap_rows_with_c1_usage,
    snap.snap_rows_with_c1_usage - src.src_rows_with_c1_usage AS c1_usage_diff,
    src.src_rows_with_bseg,
    snap.snap_rows_with_bseg,
    snap.snap_rows_with_bseg - src.src_rows_with_bseg AS bseg_diff,
    src.src_rows_with_sa,
    snap.snap_rows_with_sa,
    snap.snap_rows_with_sa - src.src_rows_with_sa AS sa_diff,
    src.src_rows_with_acct,
    snap.snap_rows_with_acct,
    snap.snap_rows_with_acct - src.src_rows_with_acct AS acct_diff
FROM src
CROSS JOIN snap;

-- 6e) Raw-code-only audit for end-user-facing fields
WITH expected AS (
    SELECT 'DIVISION_CD' AS code_column, 'DIVISION_DESC' AS expected_desc_column, 'business translation required' AS note FROM dual UNION ALL
    SELECT 'BO_STATUS_REASON_CD', 'BO_STATUS_REASON_DESC', 'usage reason translation required' FROM dual UNION ALL
    SELECT 'US_BO_STATUS_REASON_CD', 'US_BO_STATUS_REASON_DESC', 'subscription reason translation required' FROM dual
)
SELECT
    e.code_column,
    e.expected_desc_column,
    e.note,
    CASE WHEN c.column_name IS NULL THEN 'MISSING_DESC_COLUMN' ELSE 'DESC_COLUMN_PRESENT' END AS status
FROM expected e
LEFT JOIN all_tab_columns c
    ON c.owner = 'CISADM'
   AND c.table_name = 'D1_USAGE_RPT_CURR'
   AND c.column_name = e.expected_desc_column
ORDER BY e.code_column;
