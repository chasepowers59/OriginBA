-- 02_optimized_agg.sql
-- Required vars:
--   define start_ts = 2026-01-01
--   define end_ts   = 2026-01-08

set pagesize 50000
set linesize 220
set trimspool on

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
  NVL(SUM(spu.qty_per_usage),0) AS total_quantity
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
ORDER BY ci_cust_cl_l.descr;
