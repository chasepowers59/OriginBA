-- Smoke: verify source tables and snapshots exist with row counts.
-- Uses ALL_TABLES guard so missing snapshots return NULL instead of ORA-942.

SELECT 'CI_BILL' AS entity,
       1 AS table_exists,
       (SELECT COUNT(*) FROM cisadm.ci_bill) AS row_count
FROM dual
UNION ALL
SELECT 'CI_BSEG', 1, (SELECT COUNT(*) FROM cisadm.ci_bseg) FROM dual
UNION ALL
SELECT 'CI_FT', 1, (SELECT COUNT(*) FROM cisadm.ci_ft) FROM dual
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'FT_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'PAY_TNDR_CASH_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.pay_tndr_cash_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'WORKFLOW_QUEUE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'D1_USAGE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr) ELSE NULL END
FROM dual
UNION ALL
SELECT 'FIELD_ACTIVITY_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FIELD_ACTIVITY_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FIELD_ACTIVITY_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.field_activity_rpt_curr) ELSE NULL END
FROM dual;
