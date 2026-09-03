# Newark REP8 Aged Balance — JRS2C2M support objects

Legacy static report `REP8_Aged_Balance` queries `JRS2C2M` objects. On Newark TEST 25.4 the schema was empty; live views over `CI_FT` fixed missing-object errors but were too slow for interactive use (~25M receivable FT rows × correlated subqueries in JRXML).

## Schema placement: CISADM table + JRS2C2M synonym

| Layer | Object | Why |
|-------|--------|-----|
| **CISADM** | `NEWARK_REP8_AGED_BALANCE` table, `REFRESH_*` procedure | Has tablespace quota for ~52k-row nightly load (JRS2C2M has no quota on Newark TEST). |
| **JRS2C2M** | Synonym + `CM_*` views + `_CURR` view | Legacy report uses `RPT_SCHEMA=JRS2C2M`; synonym keeps JRXML unchanged. |

This is the same pattern as `CMS_SA_SNAPSHOT` (physical in CISADM, consumed by reporting).

## Objects

| Object | Role |
|--------|------|
| `CM_RECEIVABLES` (view) | FT grain input for bucket math |
| `CM_AGED_BALANCE` (view) | Account demographics |
| `NEWARK_REP8_AGED_BALANCE` (table in CISADM, synonym in JRS2C2M) | Nightly account-grain staging (full REP8 row) |
| `REFRESH_NEWARK_REP8_AGED_BALANCE` (proc in CISADM) | Rebuild one `rpt_dt` slice |
| `NEWARK_REP8_AGED_BALANCE_CURR` (view) | Latest `rpt_dt` slice for quick reads |
| `JOB_REFRESH_NEWARK_REP8_AGED_BALANCE` | Optional nightly job in CISADM (created **disabled**) |

## Deploy (Newark TEST)

```bash
# Prerequisites (if not already deployed)
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/01_cm_receivables_view.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/02_cm_aged_balance_view.sql

# Staging stack
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/04_newark_rep8_aged_balance_table.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/05_refresh_newark_rep8_aged_balance_procedure.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/06_newark_rep8_aged_balance_curr_view.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/07_schedule_newark_rep8_job.sql

# Initial load (allow up to ~60 min on large FT history)
DB_CALL_TIMEOUT_MS=3600000 python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/09_run_refresh.sql

# Validation
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/08_validate_newark_rep8_aged_balance.sql
```

Manual refresh:

```sql
BEGIN
  cisadm.refresh_newark_rep8_aged_balance(TRUNC(SYSDATE));
END;
/
```

Enable nightly job after first successful refresh:

```sql
EXEC DBMS_SCHEDULER.ENABLE('CISADM.JOB_REFRESH_NEWARK_REP8_AGED_BALANCE');
```

## JRXML change

Replace the `REP8_VW` subDataset SQL with `rep8_vw_jrxml_query.sql` (simple `SELECT` from `NEWARK_REP8_AGED_BALANCE` filtered by `Report_Date`). No correlated subqueries remain in the report.

## Validation strategy

1. **Row count** — staging rows = `CM_AGED_BALANCE` population for the slice.
2. **Total current balance** — `SUM(current_bal)` matches `CMS_SA_SNAPSHOT` LDAY `SUM(cur_bal)` for the same `rpt_dt`.
3. **Total arrears** — `SUM(arrears_total)` matches `CMS_SA_SNAPSHOT` `SUM(ars_amt2..5)` by account rollup.
4. **Read timing** — `SELECT COUNT(*) FROM NEWARK_REP8_AGED_BALANCE_CURR` completes in seconds.

Refresh `CMS_SA_SNAPSHOT` before `REFRESH_NEWARK_REP8_AGED_BALANCE` (`09_run_refresh.sql` does both).

## Notes

- Balance and aging buckets roll up **governed FIFO aging** from `CMS_SA_SNAPSHOT` (includes PS/PX payment offsets; excludes future `ARS_DT`).
- REP8 column mapping: `new_charges` = `ars_amt1` (0–30), `arrears_30_*` = `ars_amt2`, `arrears_60_*` = `ars_amt3`, `arrears_90_*` = `ars_amt4` + `ars_amt5`, `arrears_total` = sum of `ars_amt2..5`. Interest columns are zero (SA snapshot does not split LPC principal/interest).
- `STATUS` is a **legacy alias** of `COLL_CL_CD` (collection class) — not account active/inactive and not customer class. Use `CUST_CL_*` for customer class and `HAS_ACTIVE_SA` / `INACTIVE_ONLY_SW` / `SA_STATUS_SUMMARY` for inactive identification.
- Does **not** modify shared `REFRESH_CMS_SA_SNAPSHOT` source; consumes its LDAY slice.

## Column extension (2026-09-03)

After the base table exists, apply:

```bash
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/clients/newark/rep8_aged_balance/04b_alter_newark_rep8_aged_balance_columns.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/clients/newark/rep8_aged_balance/02_cm_aged_balance_view.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/clients/newark/rep8_aged_balance/05_refresh_newark_rep8_aged_balance_procedure.sql
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --file sql/clients/newark/rep8_aged_balance/06_newark_rep8_aged_balance_curr_view.sql
```

Then re-run `09_run_refresh.sql`.
- Domain import work is optional; a future Domain can be a single flat table over `NEWARK_REP8_AGED_BALANCE`.
