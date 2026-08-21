# Billed usage snapshot — bill cycle fix

## Problem

On converted clients (especially Odessa DEV), `CI_BILL.BILL_CYC_CD` and `CI_BSEG.BILL_CYC_CD` are often blank or whitespace-padded while `CI_ACCT.BILL_CYC_CD` is populated. Snapshot refresh procedures were copying only bill/bseg fields, leaving `bill_bill_cyc_cd` and `bseg_bill_cyc_cd` unpopulated in `*_RPT_CURR` tables.

## Fix (procedure SQL only — no source table changes)

| Snapshot column | New source expression |
|-----------------|----------------------|
| `bill_bill_cyc_cd` | `COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))` |
| `bseg_bill_cyc_cd` | `COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))` |

Lookup joins (`CI_BILL_CYC_L`) use the same COALESCE keys, with `TRIM()` on the lookup side:

```sql
ON TRIM(bill_bill_cyc_l.bill_cyc_cd) = COALESCE(...)
```

Oracle blank-pads only for CHAR/literal compares. `TRIM(...)` returns `VARCHAR2`, so `CHAR = TRIM(...)` never matches (`'45  ' != '45'`), which leaves `*_bill_cyc_desc` null even when codes are populated from account.

**Files updated:** all `02_refresh_*`, `02a_full_history_*`, `10_rolling_*`, and `11_rolling_*` under `bseg_billed_usage/` and `bseg_sq_usage/`.

**Already correct:** `FT_RPT_CURR`, `FT_GL_DISTRIBUTION_RPT_CURR` (account `bill_cyc_cd`).

## QA policy

| Client | Role |
|--------|------|
| **Ellensburg** | Development/reference DB — run read-only source and snapshot audits here first |
| **Target client** | Run the same read-only audit before and after promotion |

```bash
# Read-only QA (Ellensburg first, then target client)
python3 scripts/local/run_client_oracle_sql.py --client ellensburg \
  --file sql/performance/snapshots/billed_usage/qa/bill_cycle_source_audit.sql
```

## Before full refresh on a target client

1. Run audit on Ellensburg — confirm COALESCE simulation still matches expectations
2. Run audit on target client — record current snapshot coverage
3. Deploy updated procedures only after review
4. Run `02a_full_history_refresh_procedure.sql` (full history)
5. Re-run audit — expect bill-cycle coverage to match source rows where trimmed fallback resolves
6. Switch scheduled job to the rolling refresh procedure for ongoing maintenance

## Odessa DEV validation result

- `BSEG_BILLED_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `5,061,911 / 5,061,916`
- `BSEG_SQ_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `1,699,798 / 1,699,801`
