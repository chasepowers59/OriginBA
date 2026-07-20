-- Prerequisite: snapshot table existence and date coverage for periodic reports.
-- Informational — tolerates missing snapshot tables (table_exists = 0).

PROMPT === Snapshot table row counts ===

SELECT 'BSEG_SQ_USAGE_RPT_CURR' AS snapshot_name,
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR') AS table_exists,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr) END AS row_count,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR')
            THEN (SELECT MIN(bill_dt) FROM cisadm.bseg_sq_usage_rpt_curr) END AS min_dt,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_SQ_USAGE_RPT_CURR')
            THEN (SELECT MAX(bill_dt) FROM cisadm.bseg_sq_usage_rpt_curr) END AS max_dt
FROM dual
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR')
            THEN (SELECT MIN(bill_dt) FROM cisadm.bseg_billed_usage_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'BSEG_BILLED_USAGE_RPT_CURR')
            THEN (SELECT MAX(bill_dt) FROM cisadm.bseg_billed_usage_rpt_curr) END
FROM dual
UNION ALL
SELECT 'FT_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.ft_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR')
            THEN (SELECT MIN(accounting_dt) FROM cisadm.ft_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_RPT_CURR')
            THEN (SELECT MAX(accounting_dt) FROM cisadm.ft_rpt_curr) END
FROM dual
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_GL_DISTRIBUTION_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_GL_DISTRIBUTION_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_GL_DISTRIBUTION_RPT_CURR')
            THEN (SELECT MIN(accounting_dt) FROM cisadm.ft_gl_distribution_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'FT_GL_DISTRIBUTION_RPT_CURR')
            THEN (SELECT MAX(accounting_dt) FROM cisadm.ft_gl_distribution_rpt_curr) END
FROM dual
UNION ALL
SELECT 'PAY_TNDR_CASH_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.pay_tndr_cash_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR')
            THEN (SELECT MIN(pay_dt) FROM cisadm.pay_tndr_cash_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'PAY_TNDR_CASH_RPT_CURR')
            THEN (SELECT MAX(pay_dt) FROM cisadm.pay_tndr_cash_rpt_curr) END
FROM dual
UNION ALL
SELECT 'WORKFLOW_QUEUE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR')
            THEN (SELECT CAST(MIN(td_cre_dttm) AS DATE) FROM cisadm.workflow_queue_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'WORKFLOW_QUEUE_RPT_CURR')
            THEN (SELECT CAST(MAX(td_cre_dttm) AS DATE) FROM cisadm.workflow_queue_rpt_curr) END
FROM dual
UNION ALL
SELECT 'D1_USAGE_RPT_CURR',
       (SELECT COUNT(*) FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR'),
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR')
            THEN (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR')
            THEN (SELECT CAST(MIN(usage_cre_dttm) AS DATE) FROM cisadm.d1_usage_rpt_curr) END,
       CASE WHEN EXISTS (SELECT 1 FROM all_tables WHERE owner = 'CISADM' AND table_name = 'D1_USAGE_RPT_CURR')
            THEN (SELECT CAST(MAX(usage_cre_dttm) AS DATE) FROM cisadm.d1_usage_rpt_curr) END
FROM dual;

PROMPT === Calendar window boundaries (reference) ===

SELECT 'ANNUAL_START' AS boundary, TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY') AS boundary_dt FROM dual
UNION ALL
SELECT 'ANNUAL_END', TRUNC(SYSDATE, 'YYYY') FROM dual
UNION ALL
SELECT 'QUARTERLY_START', TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q') FROM dual
UNION ALL
SELECT 'QUARTERLY_END', TRUNC(SYSDATE, 'Q') FROM dual
UNION ALL
SELECT 'SEMI_ANNUAL_START', ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6) FROM dual
UNION ALL
SELECT 'SEMI_ANNUAL_END', TRUNC(SYSDATE, 'MM') FROM dual;
