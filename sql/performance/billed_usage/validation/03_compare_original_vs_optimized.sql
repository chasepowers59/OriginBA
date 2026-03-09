-- 03_compare_original_vs_optimized.sql
-- Required vars:
--   define start_ts = 2026-01-01
--   define end_ts   = 2026-01-08

set pagesize 50000
set linesize 240
set trimspool on

WITH original_agg AS (
  SELECT
    ci_cust_cl_l.descr AS customer_class,
    NVL(SUM(dscalar.quantity),0) AS original_total
  FROM CISADM.CI_ACCT ci_acct
  JOIN CISADM.CI_SA ci_sa
    ON ci_acct.acct_id = ci_sa.acct_id
  JOIN CISADM.C1_USAGE c1_usage
    ON ci_sa.sa_id = c1_usage.sa_id
   AND c1_usage.bo_status_cd = 'BD-PROC'
  JOIN CISADM.D1_USAGE d1_usage
    ON c1_usage.usage_id = d1_usage.usg_ext_id
   AND d1_usage.bo_status_cd = 'SENT'
  LEFT JOIN CISADM.D1_USAGE_SCALAR_DTL dscalar
    ON d1_usage.d1_usage_id = dscalar.d1_usage_id
  JOIN CISADM.CI_CUST_CL_L ci_cust_cl_l
    ON ci_acct.cust_cl_cd = ci_cust_cl_l.cust_cl_cd
   AND ci_cust_cl_l.language_cd = 'ENG'
  WHERE d1_usage.start_dttm >= TO_DATE('&start_ts','YYYY-MM-DD')
    AND d1_usage.start_dttm <  TO_DATE('&end_ts','YYYY-MM-DD')
  GROUP BY ci_cust_cl_l.descr
),
optimized_agg AS (
  WITH filtered_usage AS (
    SELECT D1_USAGE_ID, USG_EXT_ID
    FROM CISADM.D1_USAGE
    WHERE START_DTTM >= TO_DATE('&start_ts','YYYY-MM-DD')
      AND START_DTTM <  TO_DATE('&end_ts','YYYY-MM-DD')
      AND BO_STATUS_CD = 'SENT'
  ),
  scalar_per_usage AS (
    SELECT D1_USAGE_ID, NVL(SUM(QUANTITY),0) AS qty_per_usage
    FROM CISADM.D1_USAGE_SCALAR_DTL
    GROUP BY D1_USAGE_ID
  )
  SELECT
    ci_cust_cl_l.descr AS customer_class,
    NVL(SUM(spu.qty_per_usage),0) AS optimized_total
  FROM CISADM.CI_ACCT ci_acct
  JOIN CISADM.CI_SA ci_sa
    ON ci_acct.acct_id = ci_sa.acct_id
  JOIN CISADM.C1_USAGE c1_usage
    ON ci_sa.sa_id = c1_usage.sa_id
   AND c1_usage.bo_status_cd = 'BD-PROC'
  JOIN filtered_usage fu
    ON c1_usage.usage_id = fu.usg_ext_id
  LEFT JOIN scalar_per_usage spu
    ON fu.d1_usage_id = spu.d1_usage_id
  JOIN CISADM.CI_CUST_CL_L ci_cust_cl_l
    ON ci_acct.cust_cl_cd = ci_cust_cl_l.cust_cl_cd
   AND ci_cust_cl_l.language_cd = 'ENG'
  GROUP BY ci_cust_cl_l.descr
)
SELECT
  COALESCE(o.customer_class, p.customer_class) AS customer_class,
  NVL(o.original_total, 0) AS original_total,
  NVL(p.optimized_total, 0) AS optimized_total,
  NVL(p.optimized_total, 0) - NVL(o.original_total, 0) AS difference
FROM original_agg o
FULL OUTER JOIN optimized_agg p
  ON o.customer_class = p.customer_class
ORDER BY COALESCE(o.customer_class, p.customer_class);
