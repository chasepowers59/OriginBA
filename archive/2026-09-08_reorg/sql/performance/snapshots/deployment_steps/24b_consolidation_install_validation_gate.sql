-- Install gate: post-load sanity for all 12 consolidation snapshots.
-- Returns rows only on failure (empty result set = pass).

SELECT 'ACCT_CUSTOMER_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.acct_customer_rpt_curr) = 0
UNION ALL
SELECT 'ACCT_CUSTOMER_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_acct_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT acct_id FROM cisadm.acct_customer_rpt_curr GROUP BY acct_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'CASE_PREM_CONTACT_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.case_prem_contact_rpt_curr) = 0
UNION ALL
SELECT 'CASE_PREM_CONTACT_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_case_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT case_id FROM cisadm.case_prem_contact_rpt_curr GROUP BY case_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'NEW_SERVICE_PIPELINE_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.new_service_pipeline_rpt_curr) = 0
UNION ALL
SELECT 'NEW_SERVICE_PIPELINE_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_sa_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT sa_id FROM cisadm.new_service_pipeline_rpt_curr GROUP BY sa_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'FIELD_ACTIVITY_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.field_activity_rpt_curr) = 0
UNION ALL
SELECT 'FIELD_ACTIVITY_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_d1_activity_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT d1_activity_id FROM cisadm.field_activity_rpt_curr GROUP BY d1_activity_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'CREW_OPS_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.crew_ops_rpt_curr) = 0
UNION ALL
SELECT 'CREW_OPS_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_crew_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT crew_id FROM cisadm.crew_ops_rpt_curr GROUP BY crew_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'DEVICE_SP_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.device_sp_rpt_curr) = 0
UNION ALL
SELECT 'DEVICE_SP_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_d1_dvc_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT d1_dvc_id FROM cisadm.device_sp_rpt_curr GROUP BY d1_dvc_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'PAY_EVENT_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.pay_event_rpt_curr) = 0
UNION ALL
SELECT 'PAY_EVENT_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_pay_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT pay_id FROM cisadm.pay_event_rpt_curr GROUP BY pay_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'BILLABLE_CHARGE_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.billable_charge_rpt_curr) = 0
UNION ALL
SELECT 'BILLABLE_CHARGE_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_charge_line_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT billable_chg_id, line_seq FROM cisadm.billable_charge_rpt_curr
      GROUP BY billable_chg_id, line_seq HAVING COUNT(*) > 1)

UNION ALL
SELECT 'SA_AGED_BAL_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.sa_aged_bal_rpt_curr) = 0
UNION ALL
SELECT 'SA_AGED_BAL_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_sa_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT sa_id FROM cisadm.sa_aged_bal_rpt_curr GROUP BY sa_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'WO_PROC_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.wo_proc_rpt_curr) = 0
UNION ALL
SELECT 'WO_PROC_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_wo_proc_id_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT wo_proc_id FROM cisadm.wo_proc_rpt_curr GROUP BY wo_proc_id HAVING COUNT(*) > 1)

UNION ALL
SELECT 'OPS_EXCEPTION_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.ops_exception_rpt_curr) = 0
UNION ALL
SELECT 'OPS_EXCEPTION_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_excp_key_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT excp_source, excp_natural_key FROM cisadm.ops_exception_rpt_curr
      GROUP BY excp_source, excp_natural_key HAVING COUNT(*) > 1)

UNION ALL
SELECT 'WORKFLOW_QUEUE_RPT_CURR', 'EMPTY_TABLE', 'Snapshot has zero rows after install'
FROM dual WHERE (SELECT COUNT(*) FROM cisadm.workflow_queue_rpt_curr) = 0
UNION ALL
SELECT 'WORKFLOW_QUEUE_RPT_CURR', 'DUPLICATE_GRAIN', 'duplicate_queue_key_groups=' || TO_CHAR(COUNT(*))
FROM (SELECT queue_source, queue_natural_key FROM cisadm.workflow_queue_rpt_curr
      GROUP BY queue_source, queue_natural_key HAVING COUNT(*) > 1);
