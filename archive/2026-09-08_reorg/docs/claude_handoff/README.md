# Claude Handoff Pack (OriginBA operations)

Download this entire folder and give it to Claude Co-work / Claude Desktop.

**GitHub:** `docs/claude_handoff/` on `main`  
**Related:** `docs/cowork/` (skills + system directions)

## What's inside

| File | Contents |
|------|----------|
| `01_connections.md` | All Oracle client aliases, hosts/services, `.env` key schema, Jaspersoft DS aliases |
| `02_db_execution_method.md` | How Cursor queries C2M (runner, thick mode, limits) |
| `03_confirmed_facts.md` | Empirically confirmed filters (active SA, ARS, balance-forward, lookups) |
| `04_snapshot_pipelines.md` | Active 7 snapshots, deploy sequence, Newark 2yr cutover |
| `05_jaspersoft_promotion.md` | Client + environment promotion pipelines |
| `06_procedures_and_scripts_index.md` | Scripts, SQL packs, QA helpers |
| `07_mcp_bridge_setup.md` | Register read-only MCP on the VPN Mac |
| `mcp/` | Config snippet + pointer to `scripts/local/originba_oracle_mcp.py` |

## Quick start for Claude

1. Read `01_connections.md` + `02_db_execution_method.md` + `03_confirmed_facts.md` first.
2. Prefer live SQL via MCP (`originba_run_readonly_sql`) once Chase registers it.
3. Until MCP is up: ask Chase/Cursor to run `scripts/local/run_client_oracle_sql.py`.
4. Never request passwords. Never suggest DML against C2M source tables.
5. Default validation client: `int_dev` (Origin DEV). Client TEST: `ellensburg`, `newark`, etc.

## Security

- No passwords in this pack.
- Live queries use personal `CPOWERS` (contract: read-only).
- Jaspersoft datasource user `JRS2C2M` is separate (server DS overlays only).
- Production aliases exist but MCP disables `*_prod` by default.
