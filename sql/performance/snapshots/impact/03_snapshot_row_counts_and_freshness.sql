-- Purpose:
--   Show live row counts and latest load timestamp for each snapshot table.

SELECT 'billing' AS workstream, 'BSEG_BILLED_USAGE_RPT_CURR' AS table_name, COUNT(*) AS live_row_count, MIN(load_dttm) AS min_load_dttm, MAX(load_dttm) AS max_load_dttm
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'billing', 'BSEG_SQ_USAGE_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'finance', 'FT_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'finance', 'FT_GL_DISTRIBUTION_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'debt_mgmt', 'ACCT_DEBT_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.acct_debt_rpt_curr
UNION ALL
SELECT 'debt_mgmt', 'COLL_PROC_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.coll_proc_rpt_curr
UNION ALL
SELECT 'meter_ops', 'D1_USAGE_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'meter_ops', 'D1_USAGE_SCALAR_DTL_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL
SELECT 'meter_ops', 'D1_MSRMT_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.d1_msrmt_rpt_curr
UNION ALL
SELECT 'payments_cashiering', 'PAY_TNDR_CASH_RPT_CURR', COUNT(*), MIN(load_dttm), MAX(load_dttm)
FROM cisadm.pay_tndr_cash_rpt_curr;
