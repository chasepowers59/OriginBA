# Billed usage snapshot — bill cycle fix

## Problem

On converted clients (especially Odessa DEV), `CI_BILL.BILL_CYC_CD` and `CI_BSEG.BILL_CYC_CD` are often blank or whitespace-padded while `CI_ACCT.BILL_CYC_CD` is populated. Snapshot refresh procedures were copying only bill/bseg fields, leaving `bill_bill_cyc_cd` and `bseg_bill_cyc_cd` unpopulated in `*_RPT_CURR` tables.

## Fix (procedure SQL only — no source table changes)

| Snapshot column | New source expression |
|-----------------|----------------------|
| `bill_bill_cyc_cd` | `COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))` |
| `bseg_bill_cyc_cd` | `COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))` |

Lookup joins (`CI_BILL_CYC_L`) use the same COALESCE keys.

**Files updated:** all `02_refresh_*`, `02a_full_history_*`, `10_rolling_*`, and `11_rolling_*` under `bseg_billed_usage/` and `bseg_sq_usage/`.

**Already correct:** `FT_RPT_CURR`, `FT_GL_DISTRIBUTION_RPT_CURR` (account `bill_cyc_cd`).

## QA policy

| Client | Role |
|--------|------|
| **CityCorp** | Read-only reference — run `qa/bill_cycle_source_audit.sql` |
| **Odessa DEV** | Only DB we deploy procedures to and run full refresh |

```bash
# Read-only QA (CityCorp or Odessa)
python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/billed_usage/qa/bill_cycle_source_audit.sql

# Deploy + refresh (Odessa DEV ONLY)
python3 scripts/local/run_client_oracle_sql.py --client odessa_dev \
  --file sql/performance/snapshots/billed_usage/bseg_billed_usage/02a_full_history_refresh_procedure.sql
# then compile/run procedure via SQL*Plus or run_client_oracle_sql with BEGIN/END block
```

## Before full refresh on Odessa

1. Run audit on CityCorp — confirm COALESCE simulation matches expectations
2. Run audit on Odessa — confirm current snapshots are 0% populated
3. Deploy updated procedures to **Odessa DEV only**
4. Run `02a_full_history_refresh_procedure.sql` (full history)
5. Re-run audit — expect bill-cycle coverage to match source rows where trimmed fallback resolves
6. Switch scheduled job to `02_refresh_snapshot_procedure_6month.sql` for rolling maintenance

## Odessa DEV validation result

- `BSEG_BILLED_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `5,061,911 / 5,061,916`
- `BSEG_SQ_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `1,699,798 / 1,699,801`
