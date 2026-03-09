-- 01_original_agg.sql
-- Required vars:
--   define start_ts = 2026-01-01
--   define end_ts   = 2026-01-08

set pagesize 50000
set linesize 220
set trimspool on

SELECT
  ci_cust_cl_l.descr AS customer_class,
  NVL(SUM(dscalar.quantity),0) AS total_quantity
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
ORDER BY ci_cust_cl_l.descr;
