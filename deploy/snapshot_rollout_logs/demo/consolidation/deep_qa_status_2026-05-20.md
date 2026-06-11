# Demo Consolidation Snapshot Deep QA

**Date:** 2026-05-20  
**Client:** demo  
**Scope:** Population parity, join/filter audit, lookup coverage for all 12 workstream consolidation snapshots

## Design principle validated

Snapshots use **`02a` full-history refresh** for ad hoc Domain consumption: preserve driving population, enrich with **LEFT JOIN** lookups/BODA views, and **do not apply workstream UI filters in SQL**. Rolling **`02`** procedures may retain 6-month windows and operational scope for scheduled refresh.

## Population parity (post-fix)

| Snapshot | Driving grain | Source count | Snapshot | Parity |
|---|---|---:|---:|---|
| `ACCT_CUSTOMER_RPT_CURR` | `CI_ACCT` | 1,049 | 1,049 | PASS |
| `CASE_PREM_CONTACT_RPT_CURR` | `CI_CASE` | 14 | 14 | PASS |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | `CI_SA` (all) | 6,643 | 6,643 | PASS (was 3,832 — status/proposal WHERE removed from `02a`) |
| `FIELD_ACTIVITY_RPT_CURR` | D1FA activities | 5,210 | 5,210 | PASS |
| `CREW_OPS_RPT_CURR` | `C1_REPRESENTATIVE` | 44 | 44 | PASS (was 51 — BODA view fan-out deduped) |
| `DEVICE_SP_RPT_CURR` | `D1_DVC` | 5,086 | 5,086 | PASS |
| `PAY_EVENT_RPT_CURR` | `CI_PAY` | 39,701 | 39,701 | PASS |
| `BILLABLE_CHARGE_RPT_CURR` | `CI_B_CHG_LINE` | 18,127 | 18,127 | PASS (was 17 — INNER `CI_SA`/lookups dropped orphan SA lines) |
| `SA_AGED_BAL_RPT_CURR` | Governed arrears FT | 5,408 | 5,408 | PASS (was 3,633 — active-only filter + INNER enrichment removed from `02a`) |
| `WO_PROC_RPT_CURR` | `CI_WO_PROC` | 1,637 | 1,637 | PASS |
| `OPS_EXCEPTION_RPT_CURR` | Exception union | 683,761 | 683,761 | PASS (USAGE branch: INNER `D1_USAGE` → LEFT JOIN; was 560,109) |
| `WORKFLOW_QUEUE_RPT_CURR` | TODO + batch | 308,676 + 176,134 | match | PASS |

## Fixes applied in this pass

| Snapshot | Issue | Resolution |
|---|---|---|
| `BILLABLE_CHARGE` | INNER joins to `CI_SA`, account, SA type dropped 18,110 charge lines with missing/invalid SA | Enrichment changed to LEFT JOIN in `02a`/`02` |
| `SA_AGED_BAL` | `sa_status_flg = '20'` and INNER customer/class joins dropped 574 debt SAs | Removed status filter from `02a`; LEFT JOIN enrichment; `02` enrichment also LEFT JOIN |
| `NEW_SERVICE_PIPELINE` | Pipeline WHERE (status 10/20, proposal flags) in `02a` dropped ~2,811 SAs | Removed from `02a`; filters retained in rolling `02` only |
| `FIELD_ACTIVITY` | INNER BODA join could drop activities on clients without full BODA coverage | LEFT JOIN BODA in `02a`/`02` |
| `CREW_OPS` | BODA view has 51 rows / 44 reps (fan-out); INNER BODA dropped reps without view rows | Drive from `C1_REPRESENTATIVE`; deduped BODA via `ROW_NUMBER`; `bo_status_desc` falls back to code |
| `CASE_PREM_CONTACT` | INNER `CMS_CI_CASE_VW` could drop cases missing BODA timing | LEFT JOIN view for enrichment only |
| `OPS_EXCEPTION` (USAGE) | INNER `D1_USAGE` dropped 123,652 orphan usage exceptions on demo | LEFT JOIN `D1_USAGE` in `02a`/`02` |

## Lookup / enrichment coverage

| Snapshot | Finding | Assessment |
|---|---|---|
| `ACCT_CUSTOMER` | 0 rows with code but missing desc | PASS |
| `BILLABLE_CHARGE` | 0 rows with status code but missing desc | PASS |
| `FIELD_ACTIVITY` | 0 rows with BO status code but missing desc | PASS |
| `CREW_OPS` | All rows had missing `F1_BUS_OBJ_STATUS_L` for `ACTIVE` on demo | **Demo data gap** — mitigated with `NVL(descr, bo_status_cd)` |
| `CASE_PREM_CONTACT` | 4 rows missing `prem_address1` with `prem_id` | Source premises without address on demo |
| `NEW_SERVICE_PIPELINE` | 0 `ft_bal_*` populated | Expected — no `CM_FT_BAL` char on demo |
| `WORKFLOW_QUEUE` | 68,738 / 308,676 todo rows with `fk_acct_id` via X1 overlay | PASS |

## Business logic notes

- **`SA_AGED_BAL`**: Debt buckets use governed FT logic (`freeze_sw='Y'`, `not_in_ars_sw='N'`, exclude PS/PX, `cur_amt` aging on `ars_dt`). Deep QA parity query updated to match procedure — not legacy `tot_amt` / `ft_type_flg='BS'` shortcut.
- **`BILLABLE_CHARGE`**: Grain is charge **line** (`CI_B_CHG_LINE`); SA/account fields nullable when charge references missing SA (common on demo).
- **`NEW_SERVICE_PIPELINE`**: Full SA population in `02a` supports ad hoc status/proposal filters in JRS; rolling `02` keeps 6-month + pipeline scope for ops refresh.
- **`CASE_PREM_CONTACT`**: `CMS_CI_CASE_VW` supplies BODA timing/duration; base `CI_CASE` drives population when view row absent.

## Commands

```bash
bash scripts/local/run_consolidation_snapshot_demo_qa.sh demo
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/docs/consolidation_demo_deep_qa.sql
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/docs/consolidation_demo_qa_extended.sql
python3 scripts/local/run_client_oracle_sql.py --client demo \
  --file sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql
python3 scripts/local/audit_consolidation_snapshot_physical_sources.py
```

## Remaining acceptable exclusions

- Rolling **`02`** procedures intentionally scope by date window and workstream filters — not used for initial ad hoc Domain load (`02a`).
- **`OPS_EXCEPTION`** and **`WORKFLOW_QUEUE`** are large union snapshots; grain is exception/queue entry, not full CIS population.
- Lookup desc nulls where demo seed data lacks `*_L` / `F1_BUS_OBJ_STATUS_L` rows — codes remain filterable in ad hoc.
