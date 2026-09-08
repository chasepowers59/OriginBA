# 02 — DB execution method (how Cursor does it)

## Not MCP (today's Cursor path)

Cursor does **not** use SQLcl MCP for day-to-day C2M SQL. It shells:

```bash
python3 scripts/local/run_client_oracle_sql.py --client <alias> --sql "..."
# or
python3 scripts/local/run_client_oracle_sql.py --client <alias> --file path/to.sql
```

## Code path

1. `load_env_file(repo/.env)` — file wins over process env  
   (`scripts/local/oracle_client.py`)
2. `ensure_oracle_client(config)` — if `DB_THICK_MODE` or `ORACLE_CLIENT_LIB_DIR` set →  
   `oracledb.init_oracle_client(lib_dir=...)`
3. `client_connection(config, client)` → `(user, password, dsn)`
4. `normalize_oracle_dsn(dsn)` strips optional JDBC prefixes
5. `oracledb.connect(user=..., password=..., dsn=...)`
6. `conn.call_timeout = DB_CALL_TIMEOUT_MS`
7. Execute statements; `fetchmany(max_rows)` (default **5000**)

## Mode on Chase Mac

| Item | Value |
|------|-------|
| python-oracledb | 3.4.2 |
| Mode | **Thick** (thin before init, thick after) |
| Instant Client | 23.26.1.0.0 at `/Users/chase/Downloads/instantclient_23_26` |
| Why thick | Native Network Encryption / data integrity (`DPY-3001` in thin) |
| Origin DEV DB | Oracle 23ai 23.9.0.25.0 |

## Limits

| Control | Default |
|---------|---------|
| `--max-rows` | 5000 |
| `DB_CALL_TIMEOUT_MS` | 900000 (15 min) on this Mac |
| Read-only | Contract / process (runner itself can run DML if asked — do not) |

## Schema discipline

1. Prefer cached: `output/ai_cisadm_context.json`, dictionaries, join-path KB
2. Confirm flags live: `cisadm.ci_lookup_val_l`
3. Always `TRIM` CHAR flags: `NULLIF(TRIM(col),'')`

## Permanent SQL idioms

```sql
-- Active SA
NULLIF(TRIM(sa.sa_status_flg), '') = '20'

-- Still-owed / ARS (balance-forward clients)
ft.freeze_sw = 'Y'
AND ft.not_in_ars_sw = 'N'
AND ft.ars_dt IS NOT NULL
AND ft.redundant_sw = 'N'

-- Do NOT use MATCH_EVT_ID for paid/balanced on SmartCity clients
-- (OPEN_ITEM_SW = 'N' everywhere checked)
```
