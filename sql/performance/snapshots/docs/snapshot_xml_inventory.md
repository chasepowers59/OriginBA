# Snapshot XML Inventory

## Purpose
This document maps each governed snapshot to:
- the colocated XML copy inside the snapshot workspace
- the importable Domain XML artifact in the repository

Use it when you need to answer:
- which XML file backs a given snapshot Domain
- where the local working copy lives in the snapshot workspace
- where the importable XML lives in the repo
- how the SQL snapshot and the Jaspersoft XML artifact line up

## Locations
Active importable snapshot XML files live under:
- `domains/exports/manual_imports/`

Colocated working copies live inside each snapshot workspace under:
- `sql/performance/snapshots/<workstream>/<snapshot_folder>/`

The current snapshot XML inventory is also summarized in:
- `domains/README.md`

## Snapshot XML Map

| Snapshot | Workstream | Snapshot-folder XML copy | Importable XML file |
| --- | --- | --- | --- |
| `BSEG_BILLED_USAGE_RPT_CURR` | `billing` | `sql/performance/snapshots/billed_usage/bseg_billed_usage/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml` |
| `BSEG_SQ_USAGE_RPT_CURR` | `billing` | `sql/performance/snapshots/billed_usage/bseg_sq_usage/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml` |
| `FT_RPT_CURR` | `finance` | `sql/performance/snapshots/finance/ft_rpt_curr/FT_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/FT_RPT_CURR_End_User_Friendly.xml` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `finance` | `sql/performance/snapshots/finance/ft_gl_distribution/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml` |
| `ACCT_DEBT_RPT_CURR` | `debt_mgmt` | `sql/performance/snapshots/debt_mgmt/acct_debt/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml` |
| `COLL_PROC_RPT_CURR` | `debt_mgmt` | `sql/performance/snapshots/debt_mgmt/coll_proc/COLL_PROC_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/COLL_PROC_RPT_CURR_End_User_Friendly.xml` |
| `D1_USAGE_RPT_CURR` | `meter_ops` | `sql/performance/snapshots/meter_ops/d1_usage/D1_USAGE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/D1_USAGE_RPT_CURR_End_User_Friendly.xml` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `meter_ops` | `sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml` |
| `D1_MSRMT_RPT_CURR` | `meter_ops` | `sql/performance/snapshots/meter_ops/d1_msrmt/D1_MSRMT_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml` |
| `PAY_TNDR_CASH_RPT_CURR` | `payments_cashiering` | `sql/performance/snapshots/payments_cashiering/pay_tndr_cashier/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml` |

## Consolidation snapshot XML (12 tables)

| Snapshot | Workstream | Snapshot-folder XML copy | Importable XML file |
| --- | --- | --- | --- |
| `ACCT_CUSTOMER_RPT_CURR` | `customer_ops` | `sql/performance/snapshots/customer_ops/acct_customer/ACCT_CUSTOMER_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/ACCT_CUSTOMER_RPT_CURR_End_User_Friendly.xml` |
| `CASE_PREM_CONTACT_RPT_CURR` | `customer_ops` | `sql/performance/snapshots/customer_ops/case_prem_contact/CASE_PREM_CONTACT_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/CASE_PREM_CONTACT_RPT_CURR_End_User_Friendly.xml` |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | `new_services` | `sql/performance/snapshots/new_services/pipeline/NEW_SERVICE_PIPELINE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/NEW_SERVICE_PIPELINE_RPT_CURR_End_User_Friendly.xml` |
| `FIELD_ACTIVITY_RPT_CURR` | `field_ops` | `sql/performance/snapshots/field_ops/field_activity/FIELD_ACTIVITY_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/FIELD_ACTIVITY_RPT_CURR_End_User_Friendly.xml` |
| `CREW_OPS_RPT_CURR` | `field_ops` | `sql/performance/snapshots/field_ops/crew_ops/CREW_OPS_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/CREW_OPS_RPT_CURR_End_User_Friendly.xml` |
| `DEVICE_SP_RPT_CURR` | `meter_ops` | `sql/performance/snapshots/meter_ops/device_sp/DEVICE_SP_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/DEVICE_SP_RPT_CURR_End_User_Friendly.xml` |
| `PAY_EVENT_RPT_CURR` | `cashiering` | `sql/performance/snapshots/payments_cashiering/pay_event/PAY_EVENT_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/PAY_EVENT_RPT_CURR_End_User_Friendly.xml` |
| `BILLABLE_CHARGE_RPT_CURR` | `finance` | `sql/performance/snapshots/finance/billable_charge/BILLABLE_CHARGE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/BILLABLE_CHARGE_RPT_CURR_End_User_Friendly.xml` |
| `SA_AGED_BAL_RPT_CURR` | `debt_mgmt` | `sql/performance/snapshots/debt_mgmt/sa_aged_bal/SA_AGED_BAL_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/SA_AGED_BAL_RPT_CURR_End_User_Friendly.xml` |
| `WO_PROC_RPT_CURR` | `debt_mgmt` | `sql/performance/snapshots/debt_mgmt/wo_proc/WO_PROC_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/WO_PROC_RPT_CURR_End_User_Friendly.xml` |
| `OPS_EXCEPTION_RPT_CURR` | `common` | `sql/performance/snapshots/common/ops_exception/OPS_EXCEPTION_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/OPS_EXCEPTION_RPT_CURR_End_User_Friendly.xml` |
| `WORKFLOW_QUEUE_RPT_CURR` | `common` | `sql/performance/snapshots/common/workflow_queue/WORKFLOW_QUEUE_RPT_CURR_End_User_Friendly.xml` | `domains/exports/manual_imports/WORKFLOW_QUEUE_RPT_CURR_End_User_Friendly.xml` |

Regenerate with: `python3 scripts/build_consolidation_domain_xml.py`

## How to use these files
- Use the SQL workspace under `sql/performance/snapshots/` for table, procedure, scheduler, and validation logic.
- Use the colocated XML copy in the snapshot folder when you are building, reviewing, or debugging that snapshot end to end.
- Use the XML file under `domains/exports/manual_imports/` for Jaspersoft Domain import.
- Use the business-facing snapshot docs under `docs/` for grain, measure, and fit-for-purpose guidance.

## Maintenance rule
Whenever a new governed snapshot is added:
1. Add the importable XML to `domains/exports/manual_imports/`.
2. Copy the same XML into the matching snapshot workspace.
3. Add the mapping to this inventory.
4. Add the XML reference to the corresponding snapshot doc and snapshot README.
5. Keep the snapshot-folder copy and the importable copy synchronized whenever the Domain changes.
