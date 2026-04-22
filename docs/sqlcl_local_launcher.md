# SQLcl Local Launcher

Use these local helpers to start Oracle SQLcl for OriginBA without retyping connection details.

## Files

- `scripts/local/start_sqlcl_mcp.ps1`
- `scripts/local/open_sqlcl_db_session.ps1`
- `scripts/local/run_oracle_sql.py`
- `scripts/local/run_oracle_sql.ps1`
- local Cursor MCP config: `.cursor/mcp.json`

## What they do

`start_sqlcl_mcp.ps1`
- starts SQLcl in MCP mode
- loads `ORACLE_CLIENT_LIB_DIR`, `TNS_ADMIN`, and `JAVA_HOME` from `.env` into the current process before launch

`open_sqlcl_db_session.ps1`
- reads `DB_USER`, `DB_PASSWORD`, and `DB_CONNECT_STRING` from `.env`
- if `DB_CONNECT_STRING` is blank, builds it from `DB_HOST`, `DB_PORT`, and `DB_SERVICE_NAME`
- opens an interactive SQLcl session against the configured Oracle database

`run_oracle_sql.py` / `run_oracle_sql.ps1`
- uses `python-oracledb` from the local repo venv
- reads the same `.env` values as the rest of the local setup
- bypasses SQLcl completely for direct command-line query execution
- this is the most reliable path for local automation from this repo

## Run commands

From the repo root in PowerShell:

```powershell
.\scripts\local\start_sqlcl_mcp.ps1
```

```powershell
.\scripts\local\open_sqlcl_db_session.ps1
```

```powershell
.\scripts\local\run_oracle_sql.ps1 -Sql "select sysdate from dual"
```

## Cursor

Cursor will auto-start SQLcl MCP from:

```json
{
  "mcpServers": {
    "oracle-sqlcl": {
      "command": "C:/Users/cvpow/Downloads/sqlcl-latest/sqlcl/bin/sql.exe",
      "args": ["-mcp"]
    }
  }
}
```

stored in `.cursor/mcp.json`.

## Notes

- `.env` is ignored by git and remains the source of local credentials.
- SQLcl MCP can start without a DB connection, but schema-aware AI work requires SQLcl to be able to connect to the Oracle instance.
- If SQLcl needs Java or Oracle client settings, add `JAVA_HOME` or `TNS_ADMIN` to `.env`.
- If the SQLcl Windows launcher remains unstable, use `run_oracle_sql.ps1` for direct local DB execution and keep SQLcl only for Cursor MCP experiments.
