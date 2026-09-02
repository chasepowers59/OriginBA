# Newark REP8 Aged Balance — JRS2C2M support objects

Legacy static report `REP8_Aged_Balance` queries `JRS2C2M.CM_AGED_BALANCE` and `JRS2C2M.CM_RECEIVABLES`. Those objects were missing on Newark TEST 25.4 (empty `JRS2C2M` schema).

## Deploy (Newark TEST)

```bash
python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/01_cm_receivables_view.sql

python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/02_cm_aged_balance_view.sql

python3 scripts/local/run_client_oracle_sql.py --client newark \
  --sql-file sql/clients/newark/rep8_aged_balance/03_report_8_procedure.sql
```

## Notes

- `CM_RECEIVABLES` is a governed view over frozen `CI_FT` rows (ARS-eligible, excludes payments).
- `CM_AGED_BALANCE` maps Newark premise chars (`LOT`, `BLOCK`, `WARD`, etc.) using `adhoc_char_val` where needed.
- Bucket math remains in the JRXML `REP8_VW` subDataset (LPC split logic preserved).
- If Newark PROD has the original `REPORT_8` / table DDL, prefer exporting that for full parity.
