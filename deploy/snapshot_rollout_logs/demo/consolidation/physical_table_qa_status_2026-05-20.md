# Demo Consolidation Snapshot — Physical Table Validation

**Date:** 2026-05-20  
**Client:** demo only  
**Inputs:** `deploy/snapshot_rollout_logs/demo/table_health.json`, `output/workstream_physical_catalog.json`, `consolidation_demo_physical_table_qa.sql`, `consolidation_demo_deep_qa.sql`

## Summary

All **12 consolidation snapshots** use the correct **physical CISADM driving tables** for population on demo. After this pass, **population parity is PASS** for every snapshot (missing = 0 on all driver-grain checks).

One procedure fix was applied during validation: **`OPS_EXCEPTION`** USAGE branch used `INNER JOIN D1_USAGE`, which dropped 123,652 orphan usage exceptions on demo. Changed to **LEFT JOIN** in `02a`/`02` so `D1_USAGE_EXCP` is the full driver grain.

## Physical driver parity (demo)

| Snapshot | Physical driver | Source | Snapshot | Missing |
|---|---|---:|---:|---:|
| `ACCT_CUSTOMER` | `CI_ACCT` | 1,049 | 1,049 | 0 |
| `CASE_PREM_CONTACT` | `CI_CASE` | 14 | 14 | 0 |
| `NEW_SERVICE_PIPELINE` | `CI_SA` | 6,643 | 6,643 | 0 |
| `FIELD_ACTIVITY` | `D1_ACTIVITY` (D1FA) | 5,210 | 5,210 | 0 |
| `CREW_OPS` | `C1_REPRESENTATIVE` | 44 | 44 | 0 |
| `DEVICE_SP` | `D1_DVC` | 5,086 | 5,086 | 0 |
| `PAY_EVENT` | `CI_PAY` | 39,701 | 39,701 | 0 |
| `BILLABLE_CHARGE` | `CI_B_CHG_LINE` + `CI_BILL_CHG` | 18,127 | 18,127 | 0 |
| `SA_AGED_BAL` | Governed `CI_FT` debt SAs | 5,408 | 5,408 | 0 |
| `WO_PROC` | `CI_WO_PROC` | 1,637 | 1,637 | 0 |
| `OPS_EXCEPTION` | Union (see below) | 683,761 | 683,761 | 0 |
| `WORKFLOW_QUEUE` | `CI_TD_ENTRY` + `CI_BATCH_INST` | 308,676 + 176,134 | match | 0 |

### OPS_EXCEPTION source breakdown

| Source | Physical table | Source count | Snapshot | Missing |
|---|---|---:|---:|---:|
| BSEG | `CI_BSEG_EXCP` | 1,625 | 1,625 | 0 |
| USAGE | `D1_USAGE_EXCP` | 140,339 | 140,339 | 0 |
| VEE | `D1_VEE_EXCP` | 541,797 | 541,797 | 0 |

Natural keys: BSEG = `bseg_id~bseg_excp_flg`; USAGE = `usage_excp_id`; VEE = `vee_excp_id`.

## Custom view enrichment (LEFT JOIN only — not driving population)

Six snapshots still reference client views for optional columns. Static audit: `python3 scripts/local/audit_consolidation_snapshot_physical_sources.py`

| Snapshot | Custom views | Role |
|---|---|---|
| `CASE_PREM_CONTACT` | `CMS_CI_CASE_VW` | BODA case timing/duration |
| `FIELD_ACTIVITY` | `CMS_D1_ACTIVITY_CHAR_VW`, `CMS_D1_ACTIVITY_D1FA_BODA_VW` | Appointment flag, BODA attrs |
| `CREW_OPS` | `CMS_C1_REPRESENTATIVE_BODA_VW`, `CMS_D1_ACTIVITY_D1FA_BODA_VW` | Crew BODA, activity overlay |
| `DEVICE_SP` | `CMS_D1_DVC_CHAR_VW`, `CMS_D1_DVC_IDENTIFIER_VW`, `CMS_W1_ASSET_IDENTIFIER_VW` | Device identifiers |
| `WO_PROC` | `C1_BI_WOPROC_VW` | WO process BI overlay |
| `WORKFLOW_QUEUE` | `X1_BI_TD_ENTRY_VW` | Account linkage on to-dos |

Six snapshots are **view-free** for driving population: `acct_customer`, `new_service_pipeline`, `pay_event`, `billable_charge`, `sa_aged_bal`, `ops_exception`.

## Enrichment coverage on demo

| Snapshot | Finding | Assessment |
|---|---|---|
| `CASE_PREM_CONTACT` | 0 rows missing BODA timing from view | PASS |
| `FIELD_ACTIVITY` | 0 rows missing appointment flag | PASS |
| `DEVICE_SP` | 5,086 / 5,086 rows with null `utility_device_id` | **Demo data gap** — identifier views return no rows; device grain intact |
| `ACCT_CUSTOMER`, `BILLABLE_CHARGE`, `FIELD_ACTIVITY`, `CREW_OPS` | 0 missing lookup descriptions (deep QA) | PASS |
| `WORKFLOW_QUEUE` | TODO and BATCH counts match physical sources | PASS |

## Fix applied in this validation pass

| Snapshot | Issue | Resolution |
|---|---|---|
| `OPS_EXCEPTION` (USAGE) | `INNER JOIN D1_USAGE` dropped 88% of usage exceptions (orphan `D1_USAGE_EXCP` rows on demo) | `LEFT JOIN D1_USAGE` in `02a`/`02`; SP context columns nullable when usage parent missing |

## Table health cross-check

Demo workstream catalog: **171 populated**, 23 empty, 2 missing physical tables (from `table_health.json`). All driving tables for the 12 snapshots are populated on demo.

Notable demo gaps that affect **enrichment only** (not population):

- `DEVICE_SP`: identifier views empty → all `utility_device_id` null
- `NEW_SERVICE_PIPELINE`: no `CM_FT_BAL` char → balance columns empty (expected)
- `CREW_OPS`: `F1_BUS_OBJ_STATUS_L` missing for `ACTIVE` — mitigated with code fallback

## Commands

```bash
# Static physical-source audit
python3 scripts/local/audit_consolidation_snapshot_physical_sources.py

# Physical driver parity (18 statements)
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql

# Deep population + lookup checks
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/docs/consolidation_demo_deep_qa.sql

# Full deploy + refresh + package validation
bash scripts/local/run_consolidation_snapshot_demo_qa.sh demo
```

Logs: `deploy/snapshot_rollout_logs/demo/consolidation/physical_table_qa_run.log`
