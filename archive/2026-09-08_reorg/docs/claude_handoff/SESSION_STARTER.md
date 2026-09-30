# Claude session starter (paste)

You have the OriginBA Claude handoff pack (`docs/claude_handoff/`).

Operating rules:
1. Read `01_connections.md`, `02_db_execution_method.md`, `03_confirmed_facts.md` before inventing SQL.
2. Prefer MCP `originba_run_readonly_sql` when available; else ask for Cursor paste from `run_client_oracle_sql.py`.
3. Default client for flag/lookup baseline: `int_dev`. Client TEST validation: `ellensburg` / `newark` / etc.
4. Always TRIM CHAR flags. Active SA = `'20'`. ARS debt = freeze/not_in_ars/ars_dt. No MATCH_EVT_ID on SmartCity.
5. Never DML on C2M source tables. Snapshots only for performance cutovers.
6. Jaspersoft promotions: tenant-root light-touch; import inside tenant; client DS overlay from `deploy/jaspersoft_datasources/clients/`.
7. No passwords in chat. Cite live results as confirmed via Cursor/MCP on <date> / <client>.

If MCP is connected, first call `originba_list_clients`, then run the Q3 code-table pull on `int_dev`.
