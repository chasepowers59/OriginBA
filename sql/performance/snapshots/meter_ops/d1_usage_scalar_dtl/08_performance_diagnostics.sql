-- Performance diagnostics for CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR
-- Read-only. Use this before changing the refresh procedure.

-- 8a) How many usage-header months are being rebuilt every day?
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
)
SELECT
    TRUNC(batch_driver_dttm, 'MM') AS batch_month,
    COUNT(*) AS usage_rows
FROM usage_base
GROUP BY TRUNC(batch_driver_dttm, 'MM')
ORDER BY batch_month;

-- 8b) Scalar-detail volume by batch month
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
)
SELECT
    TRUNC(ub.batch_driver_dttm, 'MM') AS batch_month,
    COUNT(*) AS scalar_rows,
    SUM(NVL(dtl.quantity, 0)) AS quantity_sum,
    SUM(NVL(dtl.final_quantity, 0)) AS final_quantity_sum
FROM usage_base ub
JOIN cisadm.d1_usage_scalar_dtl dtl
    ON dtl.d1_usage_id = ub.d1_usage_id
GROUP BY TRUNC(ub.batch_driver_dttm, 'MM')
ORDER BY batch_month;

-- 8c) How much of the full rebuild is recent versus historical?
WITH usage_base AS (
    SELECT
        u.d1_usage_id,
        NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) AS batch_driver_dttm
    FROM cisadm.d1_usage u
    WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NOT NULL
)
SELECT
    COUNT(*) AS total_scalar_rows,
    SUM(CASE WHEN ub.batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1) THEN 1 ELSE 0 END) AS scalar_rows_last_1_month,
    SUM(CASE WHEN ub.batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -3) THEN 1 ELSE 0 END) AS scalar_rows_last_3_months,
    SUM(CASE WHEN ub.batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) THEN 1 ELSE 0 END) AS scalar_rows_last_6_months,
    SUM(CASE WHEN ub.batch_driver_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) THEN 1 ELSE 0 END) AS scalar_rows_last_12_months
FROM usage_base ub
JOIN cisadm.d1_usage_scalar_dtl dtl
    ON dtl.d1_usage_id = ub.d1_usage_id;

-- 8d) Billing bridge hit rate by batch month
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

-- 8e) Account/customer resolution scope by batch month
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
    COUNT(DISTINCT usa.sa_id) AS distinct_sa,
    COUNT(DISTINCT sa.acct_id) AS distinct_acct
FROM usage_sa usa
LEFT JOIN cisadm.ci_sa sa
    ON sa.sa_id = usa.sa_id
GROUP BY usa.batch_month
ORDER BY usa.batch_month;

-- 8f) Excluded population due to all three timestamps being null
SELECT COUNT(*) AS usage_rows_with_no_batch_driver
FROM cisadm.d1_usage u
WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)) IS NULL;
