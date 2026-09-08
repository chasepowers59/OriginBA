# 07 — MCP bridge setup (Claude Desktop / Co-work)

Gives Claude a live `originba_run_readonly_sql` tool on **Chase's VPN Mac**.

## Prerequisites

1. Corporate VPN up
2. Repo at `/Users/chase/OriginBA-3` with working `.env`
3. Instant Client at path in `ORACLE_CLIENT_LIB_DIR`
4. Python 3.13+ with: `oracledb`, `python-dotenv`, `mcp[cli]`

```bash
# MCP SDK (1.x or 2.x both work with this low-level stdio server)
pip3 install "mcp[cli]" oracledb python-dotenv
python3 scripts/local/originba_oracle_mcp.py --self-test
```

## Tools exposed

| Tool | Purpose |
|------|---------|
| `originba_list_clients` | Allowed aliases |
| `originba_run_readonly_sql(client, sql, max_rows=500)` | Read-only SELECT/WITH |

### Guardrails

- Single statement; must start with `SELECT` or `WITH`
- Blocks DML/DDL/PLSQL/`FOR UPDATE`/multi-statement
- `SET TRANSACTION READ ONLY` before each query
- Default max_rows 500; hard cap 5000
- `*_prod` disabled unless `ORIGINBA_MCP_ALLOW_PROD=1`
- Never returns passwords/DSNs
- Default MCP call timeout 2 minutes (`ORIGINBA_MCP_TIMEOUT_MS` override)

## Claude Desktop / Co-work config

**Important:** register in Claude Desktop, not Cursor.

Mac path:

`~/Library/Application Support/Claude/claude_desktop_config.json`

Merge an `mcpServers.originba-oracle` block (absolute paths). Example also in `mcp/claude_desktop_config.example.json`:

```json
{
  "mcpServers": {
    "originba-oracle": {
      "command": "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
      "args": [
        "/Users/chase/OriginBA-3/scripts/local/originba_oracle_mcp.py"
      ],
      "env": {
        "ORIGINBA_ENV_PATH": "/Users/chase/OriginBA-3/.env"
      }
    }
  }
}
```

Adjust `command` if your `python3` path differs (`which python3`).

## First live tests (after reconnect)

```text
originba_list_clients()

originba_run_readonly_sql(
  client="int_dev",
  sql="SELECT SYS_CONTEXT('USERENV','SERVICE_NAME') svc, USER usr FROM dual"
)

originba_run_readonly_sql(
  client="int_dev",
  sql="SELECT field_name, field_value, descr FROM cisadm.ci_lookup_val_l WHERE language_cd='ENG' AND field_name='SA_STATUS_FLG' ORDER BY field_value"
)
```

## Honest constraints

- Must run on the VPN Mac (private subnet DBs)
- Claude session must be connected to that local MCP
- Uses `CPOWERS` path (same as Cursor); dedicated RO DB user is a future upgrade
- For long snapshot DDL/deploy work, keep using `run_client_oracle_sql.py` explicitly — MCP is for SELECT investigation

## Script location

Canonical: `scripts/local/originba_oracle_mcp.py`  
Copy in this pack: `mcp/originba_oracle_mcp.py` (keep in sync when editing)
