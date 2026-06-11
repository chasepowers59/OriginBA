PROMPT ============================================================
PROMPT Create all 12 consolidation snapshot tables
PROMPT ============================================================

PROMPT [1/12] ACCT_CUSTOMER_RPT_CURR
@@..\customer_ops\acct_customer\01_create_snapshot_table.sql

PROMPT [2/12] CASE_PREM_CONTACT_RPT_CURR
@@..\customer_ops\case_prem_contact\01_create_snapshot_table.sql

PROMPT [3/12] NEW_SERVICE_PIPELINE_RPT_CURR
@@..\new_services\pipeline\01_create_snapshot_table.sql

PROMPT [4/12] FIELD_ACTIVITY_RPT_CURR
@@..\field_ops\field_activity\01_create_snapshot_table.sql

PROMPT [5/12] CREW_OPS_RPT_CURR
@@..\field_ops\crew_ops\01_create_snapshot_table.sql

PROMPT [6/12] DEVICE_SP_RPT_CURR
@@..\meter_ops\device_sp\01_create_snapshot_table.sql

PROMPT [7/12] PAY_EVENT_RPT_CURR
@@..\payments_cashiering\pay_event\01_create_snapshot_table.sql

PROMPT [8/12] BILLABLE_CHARGE_RPT_CURR
@@..\finance\billable_charge\01_create_snapshot_table.sql

PROMPT [9/12] SA_AGED_BAL_RPT_CURR
@@..\debt_mgmt\sa_aged_bal\01_create_snapshot_table.sql

PROMPT [10/12] WO_PROC_RPT_CURR
@@..\debt_mgmt\wo_proc\01_create_snapshot_table.sql

PROMPT [11/12] OPS_EXCEPTION_RPT_CURR
@@..\common\ops_exception\01_create_snapshot_table.sql

PROMPT [12/12] WORKFLOW_QUEUE_RPT_CURR
@@..\common\workflow_queue\01_create_snapshot_table.sql
