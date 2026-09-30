# Consolidation Snapshot Deployment Manifest

Source-of-truth map for the 12 workstream consolidation snapshots. All use a **6-month rolling window** in operational mode (`02_refresh_snapshot_procedure.sql`).

| Snapshot | Table | Grain | Table Script | Baseline (`02a`) | Operational (`02`) | Validation | Rolling Window |
|---|---|---|---|---|---|---|
| `ACCT_CUSTOMER_RPT_CURR` | `ACCT_CUSTOMER_RPT_CURR` | `ACCT_ID` | `customer_ops/acct_customer/01_create_snapshot_table.sql` | `customer_ops/acct_customer/02a_full_history_refresh_procedure.sql` | `customer_ops/acct_customer/02_refresh_snapshot_procedure.sql` | `customer_ops/acct_customer/04_validation_queries.sql` | 6 months |
| `CASE_PREM_CONTACT_RPT_CURR` | `CASE_PREM_CONTACT_RPT_CURR` | `CASE_ID` | `customer_ops/case_prem_contact/01_create_snapshot_table.sql` | `customer_ops/case_prem_contact/02a_full_history_refresh_procedure.sql` | `customer_ops/case_prem_contact/02_refresh_snapshot_procedure.sql` | `customer_ops/case_prem_contact/04_validation_queries.sql` | 6 months |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | `NEW_SERVICE_PIPELINE_RPT_CURR` | `SA_ID` | `new_services/pipeline/01_create_snapshot_table.sql` | `new_services/pipeline/02a_full_history_refresh_procedure.sql` | `new_services/pipeline/02_refresh_snapshot_procedure.sql` | `new_services/pipeline/04_validation_queries.sql` | 6 months |
| `FIELD_ACTIVITY_RPT_CURR` | `FIELD_ACTIVITY_RPT_CURR` | `D1_ACTIVITY_ID` | `field_ops/field_activity/01_create_snapshot_table.sql` | `field_ops/field_activity/02a_full_history_refresh_procedure.sql` | `field_ops/field_activity/02_refresh_snapshot_procedure.sql` | `field_ops/field_activity/04_validation_queries.sql` | 6 months |
| `CREW_OPS_RPT_CURR` | `CREW_OPS_RPT_CURR` | `CREW_ID` | `field_ops/crew_ops/01_create_snapshot_table.sql` | `field_ops/crew_ops/02a_full_history_refresh_procedure.sql` | `field_ops/crew_ops/02_refresh_snapshot_procedure.sql` | `field_ops/crew_ops/04_validation_queries.sql` | 6 months |
| `DEVICE_SP_RPT_CURR` | `DEVICE_SP_RPT_CURR` | `D1_DVC_ID` | `meter_ops/device_sp/01_create_snapshot_table.sql` | `meter_ops/device_sp/02a_full_history_refresh_procedure.sql` | `meter_ops/device_sp/02_refresh_snapshot_procedure.sql` | `meter_ops/device_sp/04_validation_queries.sql` | 6 months |
| `PAY_EVENT_RPT_CURR` | `PAY_EVENT_RPT_CURR` | `PAY_ID` | `payments_cashiering/pay_event/01_create_snapshot_table.sql` | `payments_cashiering/pay_event/02a_full_history_refresh_procedure.sql` | `payments_cashiering/pay_event/02_refresh_snapshot_procedure.sql` | `payments_cashiering/pay_event/04_validation_queries.sql` | 6 months |
| `BILLABLE_CHARGE_RPT_CURR` | `BILLABLE_CHARGE_RPT_CURR` | `BILLABLE_CHG_ID`, `LINE_SEQ` | `finance/billable_charge/01_create_snapshot_table.sql` | `finance/billable_charge/02a_full_history_refresh_procedure.sql` | `finance/billable_charge/02_refresh_snapshot_procedure.sql` | `finance/billable_charge/04_validation_queries.sql` | 6 months |
| `SA_AGED_BAL_RPT_CURR` | `SA_AGED_BAL_RPT_CURR` | `SA_ID` | `debt_mgmt/sa_aged_bal/01_create_snapshot_table.sql` | `debt_mgmt/sa_aged_bal/02a_full_history_refresh_procedure.sql` | `debt_mgmt/sa_aged_bal/02_refresh_snapshot_procedure.sql` | `debt_mgmt/sa_aged_bal/04_validation_queries.sql` | 6 months |
| `WO_PROC_RPT_CURR` | `WO_PROC_RPT_CURR` | `WO_PROC_ID` | `debt_mgmt/wo_proc/01_create_snapshot_table.sql` | `debt_mgmt/wo_proc/02a_full_history_refresh_procedure.sql` | `debt_mgmt/wo_proc/02_refresh_snapshot_procedure.sql` | `debt_mgmt/wo_proc/04_validation_queries.sql` | 6 months |
| `OPS_EXCEPTION_RPT_CURR` | `OPS_EXCEPTION_RPT_CURR` | `EXCP_SOURCE`, `EXCP_NATURAL_KEY` | `common/ops_exception/01_create_snapshot_table.sql` | `common/ops_exception/02a_full_history_refresh_procedure.sql` | `common/ops_exception/02_refresh_snapshot_procedure.sql` | `common/ops_exception/04_validation_queries.sql` | 6 months |
| `WORKFLOW_QUEUE_RPT_CURR` | `WORKFLOW_QUEUE_RPT_CURR` | `QUEUE_SOURCE`, `QUEUE_NATURAL_KEY` | `common/workflow_queue/01_create_snapshot_table.sql` | `common/workflow_queue/02a_full_history_refresh_procedure.sql` | `common/workflow_queue/02_refresh_snapshot_procedure.sql` | `common/workflow_queue/04_validation_queries.sql` | 6 months |

## Procedure names

| Refresh procedure |
|---|
| `CISADM.REFRESH_ACCT_CUSTOMER_RPT_CURR` |
| `CISADM.REFRESH_CASE_PREM_CONTACT_RPT_CURR` |
| `CISADM.REFRESH_NEW_SERVICE_PIPELINE_RPT_CURR` |
| `CISADM.REFRESH_FIELD_ACTIVITY_RPT_CURR` |
| `CISADM.REFRESH_CREW_OPS_RPT_CURR` |
| `CISADM.REFRESH_DEVICE_SP_RPT_CURR` |
| `CISADM.REFRESH_PAY_EVENT_RPT_CURR` |
| `CISADM.REFRESH_BILLABLE_CHARGE_RPT_CURR` |
| `CISADM.REFRESH_SA_AGED_BAL_RPT_CURR` |
| `CISADM.REFRESH_WO_PROC_RPT_CURR` |
| `CISADM.REFRESH_OPS_EXCEPTION_RPT_CURR` |
| `CISADM.REFRESH_WORKFLOW_QUEUE_RPT_CURR` |

## Notes

- Deploy **`02a`** for the one-time full-history baseline, then replace with **`02`** before scheduling recurring jobs.
- Baseline jobs are ordered light-to-heavy; `OPS_EXCEPTION` and `WORKFLOW_QUEUE` run last.
- Operational refreshes preserve history outside the 6-month rolling scope (same model as the active 7 snapshots).
- Supplemental population QA (optional, recommended on first client): `sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql`
- Demo reference QA: `bash scripts/local/run_consolidation_snapshot_demo_qa.sh demo`
