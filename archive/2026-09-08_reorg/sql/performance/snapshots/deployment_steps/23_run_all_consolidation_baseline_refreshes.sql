PROMPT ============================================================
PROMPT Run consolidation baseline refreshes (manual foreground)
PROMPT ============================================================
PROMPT Executes all 12 full-history procedures in light-to-heavy order.

PROMPT [1/12] ACCT_CUSTOMER_RPT_CURR
BEGIN cisadm.refresh_acct_customer_rpt_curr; END;
/

PROMPT [2/12] CASE_PREM_CONTACT_RPT_CURR
BEGIN cisadm.refresh_case_prem_contact_rpt_curr; END;
/

PROMPT [3/12] CREW_OPS_RPT_CURR
BEGIN cisadm.refresh_crew_ops_rpt_curr; END;
/

PROMPT [4/12] WO_PROC_RPT_CURR
BEGIN cisadm.refresh_wo_proc_rpt_curr; END;
/

PROMPT [5/12] SA_AGED_BAL_RPT_CURR
BEGIN cisadm.refresh_sa_aged_bal_rpt_curr; END;
/

PROMPT [6/12] NEW_SERVICE_PIPELINE_RPT_CURR
BEGIN cisadm.refresh_new_service_pipeline_rpt_curr; END;
/

PROMPT [7/12] FIELD_ACTIVITY_RPT_CURR
BEGIN cisadm.refresh_field_activity_rpt_curr; END;
/

PROMPT [8/12] DEVICE_SP_RPT_CURR
BEGIN cisadm.refresh_device_sp_rpt_curr; END;
/

PROMPT [9/12] PAY_EVENT_RPT_CURR
BEGIN cisadm.refresh_pay_event_rpt_curr; END;
/

PROMPT [10/12] BILLABLE_CHARGE_RPT_CURR
BEGIN cisadm.refresh_billable_charge_rpt_curr; END;
/

PROMPT [11/12] WORKFLOW_QUEUE_RPT_CURR
BEGIN cisadm.refresh_workflow_queue_rpt_curr; END;
/

PROMPT [12/12] OPS_EXCEPTION_RPT_CURR
BEGIN cisadm.refresh_ops_exception_rpt_curr; END;
/
