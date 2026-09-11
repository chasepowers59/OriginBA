# Workstream Consolidation Snapshot Roadmap (Build Phase)

Build-only phase: Oracle table DDL and refresh procedures. No client deployment, schedulers, or JRS domains yet.

## Refresh pattern (all new snapshots)

| Procedure | Purpose |
|---|---|
| `02a_full_history_refresh_procedure.sql` | Initial load — `TRUNCATE` + full population |
| `02_refresh_snapshot_procedure.sql` | Operational — 6-month rolling window |

Procedure name: `REFRESH_<TABLE_NAME>` (same name in both files; deploy `02a` first, then replace with `02`).

## New snapshots (built)

| Workstream | Table | Grain | SQL workspace | Replaces (legacy domains) |
|---|---|---|---|---|
| Customer Operations | `ACCT_CUSTOMER_RPT_CURR` | `ACCT_ID` | `sql/performance/snapshots/customer_ops/acct_customer/` | Customer, Account Alert (account grain), C-Side (aggregates), Landlord (summary) |
| Customer Operations | `CASE_PREM_CONTACT_RPT_CURR` | `CASE_ID` | `sql/performance/snapshots/customer_ops/case_prem_contact/` | Case, Premise, Customer Contact |
| New Services | `NEW_SERVICE_PIPELINE_RPT_CURR` | `SA_ID` | `sql/performance/snapshots/new_services/pipeline/` | New Services |
| Field Operations | `FIELD_ACTIVITY_RPT_CURR` | `D1_ACTIVITY_ID` | `sql/performance/snapshots/field_ops/field_activity/` | Field Activity |
| Field Operations | `CREW_OPS_RPT_CURR` | `CREW_ID` | `sql/performance/snapshots/field_ops/crew_ops/` | Crew |
| Meter Operations | `DEVICE_SP_RPT_CURR` | `D1_DVC_ID` | `sql/performance/snapshots/meter_ops/device_sp/` | Device, Asset |
| Cashiering | `PAY_EVENT_RPT_CURR` | `PAY_ID` | `sql/performance/snapshots/payments_cashiering/pay_event/` | Payment Header, Deposit Control, Pay Plan (+ tender rollups) |
| Finance | `BILLABLE_CHARGE_RPT_CURR` | charge line key | `sql/performance/snapshots/finance/billable_charge/` | Billable Charge |
| Debt Management | `SA_AGED_BAL_RPT_CURR` | `SA_ID` | `sql/performance/snapshots/debt_mgmt/sa_aged_bal/` | SA Snapshot Aged Balance |
| Debt Management | `WO_PROC_RPT_CURR` | `WO_PROC_ID` | `sql/performance/snapshots/debt_mgmt/wo_proc/` | Write Off Process, Write Offs |
| Common | `OPS_EXCEPTION_RPT_CURR` | `(EXCP_SOURCE, EXCP_NATURAL_KEY)` | `sql/performance/snapshots/common/ops_exception/` | Bill Segment / Usage / VEE Exception |
| Common | `WORKFLOW_QUEUE_RPT_CURR` | To-Do + Batch grains | `sql/performance/snapshots/common/workflow_queue/` | To Do, Batch Process |

## Existing snapshots (unchanged)

Do not alter DDL or refresh logic for:

- `BSEG_BILLED_USAGE_RPT_CURR`, `BSEG_SQ_USAGE_RPT_CURR`
- `FT_RPT_CURR`, `FT_GL_DISTRIBUTION_RPT_CURR`
- `D1_USAGE_RPT_CURR`, `D1_USAGE_SCALAR_DTL_RPT_CURR`, `D1_MSRMT_RPT_CURR`
- `ACCT_DEBT_RPT_CURR`, `COLL_PROC_RPT_CURR`, `PAY_TNDR_CASH_RPT_CURR`

Billing join domain `Bill_Segment___Domain` — parity check against existing BSEG snapshots only; no new billing table unless gaps block reports.

Finance join domain `Financial_Transaction___Domain` — covered by existing FT snapshots; no new FT table.

## Not built yet (optional / tenant-gated)

| Table | Reason |
|---|---|
| `SEV_PROC_RPT_CURR` | Severance process — build after `00a_config_discovery_validation` confirms tenant usage |

## Validation (dev only — not deployed)

For each workspace, after `01` + `02a` in a dev schema:

```bash
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/<workstream>/<subset>/04_validation_queries.sql
```

Full consolidation QA on demo (deploy all 12 `02a`, refresh, package validation, extended null audit):

```bash
bash scripts/local/run_consolidation_snapshot_demo_qa.sh demo
python3 scripts/local/check_consolidation_field_parity.py
```

### Demo QA status (2026-05-20)

**Completed on demo with VPN.** All 12 consolidation snapshots deploy, compile VALID, and refresh successfully.

| Table | Rows | Status |
|---|---|---|
| `ACCT_CUSTOMER_RPT_CURR` | 1,049 | PASS |
| `CASE_PREM_CONTACT_RPT_CURR` | 14 | PASS |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | 3,832 | PASS |
| `FIELD_ACTIVITY_RPT_CURR` | 5,210 | PASS |
| `CREW_OPS_RPT_CURR` | 51 | PASS |
| `DEVICE_SP_RPT_CURR` | 5,086 | PASS |
| `PAY_EVENT_RPT_CURR` | 39,701 | PASS |
| `BILLABLE_CHARGE_RPT_CURR` | 17 | PASS |
| `SA_AGED_BAL_RPT_CURR` | 3,633 | PASS |
| `WO_PROC_RPT_CURR` | 1,637 | PASS |
| `OPS_EXCEPTION_RPT_CURR` | 560,109 | PASS |
| `WORKFLOW_QUEUE_RPT_CURR` | 484,810 | PASS |

Full audit log: [`deploy/snapshot_rollout_logs/demo/consolidation/qa_status_2026-05-20.md`](../deploy/snapshot_rollout_logs/demo/consolidation/qa_status_2026-05-20.md)

**Known acceptable nulls on demo:**

- `NEW_SERVICE_PIPELINE.ft_bal_*` when `CM_FT_BAL` is absent
- `CREW_OPS.bo_status_desc` for `ACTIVE` when demo has no matching `F1_BUS_OBJ_STATUS_L` row
- `CASE_PREM_CONTACT.prem_address1` for a small set of premises without address in source
- Optional to-do FK columns when no drlkey linkage (improved via `X1_BI_TD_ENTRY_VW` — ~22% todo acct coverage)

## Client deployment (ready)

Deployment wrappers and runbook are in place:

- Manifest: `sql/performance/snapshots/deployment_steps/00_consolidation_snapshot_deployment_manifest.md`
- Scripts: `21_` through `28_` in `deployment_steps/`
- Runbook: [smartcity_consolidation_snapshot_rollout_runbook.md](../docs/smartcity_consolidation_snapshot_rollout_runbook.md)
- Batch steps: `consolidation-*` in `scripts/local/run_snapshot_rollout_step.py`

Pattern: `02a` full-history baseline → `02` six-month rolling → 6-hour scheduler (04:00 GMT base, staggered away from active-7 jobs).

Domain XML (import after client validation): `domains/exports/manual_imports/*_End_User_Friendly.xml` — regenerate with `python3 scripts/build_consolidation_domain_xml.py`.

## Still deferred

- Domain XML and Standard Offering import
- Report migration from legacy domains
