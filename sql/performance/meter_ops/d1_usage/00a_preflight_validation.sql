-- Purpose:
--   Read-only preflight checks for the usage-header snapshot before
--   standardizing it into CISADM.D1_USAGE_RPT_CURR.
--
-- Goal:
--   Prove the source grain is one row per D1_USAGE header and quantify
--   how much child-detail and billing-bridge coverage exists before
--   aggregating into the snapshot.

-- 1) Source baseline from usage headers
SELECT COUNT(*) AS source_usage_rows
FROM cisadm.d1_usage;

SELECT
    d1_usage_id,
    COUNT(*) AS source_key_count
FROM cisadm.d1_usage
GROUP BY
    d1_usage_id
HAVING COUNT(*) > 1;

-- 2) Child multiplicity profile for usage-period SQ
SELECT
    COUNT(*) AS usage_with_period_sq,
    SUM(period_sq_row_count) AS total_period_sq_rows,
    SUM(CASE WHEN period_sq_row_count > 1 THEN 1 ELSE 0 END) AS usage_with_multiple_period_sq_rows
FROM (
    SELECT
        d1_usage_id,
        COUNT(*) AS period_sq_row_count
    FROM cisadm.d1_usage_period_sq
    GROUP BY
        d1_usage_id
);

-- 3) Child multiplicity profile for scalar detail
SELECT
    COUNT(*) AS usage_with_scalar_detail,
    SUM(scalar_row_count) AS total_scalar_rows,
    SUM(CASE WHEN scalar_row_count > 1 THEN 1 ELSE 0 END) AS usage_with_multiple_scalar_rows
FROM (
    SELECT
        d1_usage_id,
        COUNT(*) AS scalar_row_count
    FROM cisadm.d1_usage_scalar_dtl
    GROUP BY
        d1_usage_id
);

-- 4) Optional enrichment coverage from usage subscription and BODA detail
SELECT
    COUNT(*) AS total_usage_rows,
    SUM(CASE WHEN us.us_id IS NOT NULL THEN 1 ELSE 0 END) AS usage_with_subscription,
    SUM(CASE WHEN boda.d1_usage_id IS NOT NULL THEN 1 ELSE 0 END) AS usage_with_boda_detail
FROM cisadm.d1_usage u
LEFT JOIN cisadm.d1_us us
    ON TRIM(us.us_id) = TRIM(u.us_id)
LEFT JOIN cisadm.cms_d1_usage_boda_vw boda
    ON TRIM(boda.d1_usage_id) = TRIM(u.d1_usage_id);

-- 5) Billing-bridge candidate coverage by selected conservative match paths
WITH
path_1 AS (
    SELECT COUNT(*) AS match_count
    FROM cisadm.d1_usage u
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.usage_id) = TRIM(u.d1_usage_id)
),
path_2 AS (
    SELECT COUNT(*) AS match_count
    FROM cisadm.d1_usage u
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.master_usage_id) = TRIM(u.d1_usage_id)
),
path_3 AS (
    SELECT COUNT(*) AS match_count
    FROM cisadm.d1_usage u
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.usage_id) = TRIM(u.usg_ext_id)
    WHERE TRIM(u.usg_ext_id) IS NOT NULL
),
path_4 AS (
    SELECT COUNT(*) AS match_count
    FROM cisadm.d1_usage u
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.master_usage_id) = TRIM(u.usg_ext_id)
    WHERE TRIM(u.usg_ext_id) IS NOT NULL
)
SELECT
    'D1_USAGE_ID_TO_C1_USAGE_ID' AS bridge_path,
    (SELECT match_count FROM path_1) AS match_count
FROM dual
UNION ALL
SELECT
    'D1_USAGE_ID_TO_C1_MASTER_USAGE_ID' AS bridge_path,
    (SELECT match_count FROM path_2) AS match_count
FROM dual
UNION ALL
SELECT
    'USG_EXT_ID_TO_C1_USAGE_ID' AS bridge_path,
    (SELECT match_count FROM path_3) AS match_count
FROM dual
UNION ALL
SELECT
    'USG_EXT_ID_TO_C1_MASTER_USAGE_ID' AS bridge_path,
    (SELECT match_count FROM path_4) AS match_count
FROM dual
ORDER BY
    match_count DESC,
    bridge_path;

-- 6) Sample usage rows that bridge to billing through the most direct path
SELECT *
FROM (
    SELECT
        u.d1_usage_id,
        u.us_id,
        u.usg_ext_id,
        cu.usage_id AS c1_usage_id,
        cu.master_usage_id,
        cu.sa_id AS c1_sa_id,
        cu.bseg_id,
        cu.bo_status_cd AS c1_bo_status_cd,
        cu.start_dttm AS c1_start_dttm,
        cu.end_dttm AS c1_end_dttm
    FROM cisadm.d1_usage u
    JOIN cisadm.c1_usage cu
        ON TRIM(cu.usage_id) = TRIM(u.d1_usage_id)
    ORDER BY
        u.start_dttm DESC,
        u.d1_usage_id
)
WHERE ROWNUM <= 25;
