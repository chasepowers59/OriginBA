-- Performance diagnostics for CISADM.D1_USAGE_RPT_CURR
-- Read-only. Use this before changing the refresh procedure.

-- 9a) How many usage-header months are being rebuilt every day?
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        u.us_id,
        u.usg_ext_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
)
SELECT
    TRUNC(batch_driver_dttm, 'MM') AS batch_month,
    COUNT(*) AS usage_rows,
    COUNT(DISTINCT us_id) AS distinct_us,
    COUNT(DISTINCT usg_ext_id) AS distinct_usg_ext_id
FROM usage_base
GROUP BY TRUNC(batch_driver_dttm, 'MM')
ORDER BY batch_month;

-- 9b) How much of the full rebuild is recent versus historical?
WITH usage_base AS (
    SELECT
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
)
SELECT
    COUNT(*) AS total_usage_rows,
    SUM(CASE WHEN batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1) THEN 1 ELSE 0 END) AS usage_rows_last_1_month,
    SUM(CASE WHEN batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3) THEN 1 ELSE 0 END) AS usage_rows_last_3_months,
    SUM(CASE WHEN batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) THEN 1 ELSE 0 END) AS usage_rows_last_6_months,
    SUM(CASE WHEN batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) THEN 1 ELSE 0 END) AS usage_rows_last_12_months
FROM usage_base;

-- 9c) Billing bridge hit rate by batch month
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        u.usg_ext_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
),
bridge_counts AS (
    SELECT
        ub.d1_usage_id,
        TRUNC(ub.batch_driver_dttm, 'MM') AS batch_month,
        COUNT(cu.usage_id) AS c1_match_count
    FROM usage_base ub
    LEFT JOIN cisadm.c1_usage cu
        ON cu.usage_id = ub.usg_ext_id
       AND cu.bo_status_cd = 'BD-PROC'
    GROUP BY
        ub.d1_usage_id,
        TRUNC(ub.batch_driver_dttm, 'MM')
)
SELECT
    batch_month,
    COUNT(*) AS usage_rows,
    SUM(CASE WHEN c1_match_count = 0 THEN 1 ELSE 0 END) AS no_c1_match,
    SUM(CASE WHEN c1_match_count = 1 THEN 1 ELSE 0 END) AS one_c1_match,
    SUM(CASE WHEN c1_match_count > 1 THEN 1 ELSE 0 END) AS multi_c1_match
FROM bridge_counts
GROUP BY batch_month
ORDER BY batch_month;

-- 9d) Service agreement and account resolution scope by batch month
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        u.usg_ext_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
),
usage_bridge AS (
    SELECT
        ub.d1_usage_id,
        TRUNC(ub.batch_driver_dttm, 'MM') AS batch_month,
        cu.sa_id,
        cu.bseg_id,
        ROW_NUMBER() OVER (
            PARTITION BY ub.d1_usage_id
            ORDER BY cu.status_upd_dttm DESC NULLS LAST, cu.cre_dttm DESC NULLS LAST, cu.usage_id
        ) AS rn
    FROM usage_base ub
    LEFT JOIN cisadm.c1_usage cu
        ON cu.usage_id = ub.usg_ext_id
       AND cu.bo_status_cd = 'BD-PROC'
),
usage_sa AS (
    SELECT
        ub.batch_month,
        COALESCE(ub.sa_id, bseg.sa_id) AS sa_id
    FROM usage_bridge ub
    LEFT JOIN cisadm.ci_bseg bseg
        ON bseg.bseg_id = ub.bseg_id
    WHERE ub.rn = 1
)
SELECT
    usa.batch_month,
    COUNT(*) AS usage_rows,
    SUM(CASE WHEN usa.sa_id IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_sa,
    COUNT(DISTINCT usa.sa_id) AS distinct_sa,
    COUNT(DISTINCT sa.acct_id) AS distinct_acct
FROM usage_sa usa
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = usa.sa_id
GROUP BY usa.batch_month
ORDER BY usa.batch_month;

-- 9e) Batch-driver timestamp coverage and source null profile
SELECT
    COUNT(*) AS total_usage_rows,
    SUM(CASE WHEN u.start_dttm IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_start_dttm,
    SUM(CASE WHEN u.cre_dttm IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_cre_dttm,
    SUM(CASE WHEN u.status_upd_dttm IS NOT NULL THEN 1 ELSE 0 END) AS rows_with_status_upd_dttm,
    SUM(CASE WHEN u.start_dttm IS NULL AND u.cre_dttm IS NULL AND u.status_upd_dttm IS NULL THEN 1 ELSE 0 END) AS rows_with_no_batch_driver
FROM cisadm.d1_usage u;

-- 9f) Current snapshot load age and rebuild size
SELECT
    COUNT(*) AS snapshot_rows,
    MIN(load_dttm) AS min_load_dttm,
    MAX(load_dttm) AS max_load_dttm,
    COUNT(DISTINCT TRUNC(load_dttm)) AS distinct_load_days
FROM cisadm.d1_usage_rpt_curr;
