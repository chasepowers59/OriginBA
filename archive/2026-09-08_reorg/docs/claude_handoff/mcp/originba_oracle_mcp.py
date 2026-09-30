#!/usr/bin/env python3
"""
OriginBA read-only Oracle MCP server (stdio).

Wraps the same connection path as scripts/local/run_client_oracle_sql.py:
- .env resolution via oracle_client.load_env_file
- client_connection alias fallbacks
- thick Instant Client via ORACLE_CLIENT_LIB_DIR / DB_THICK_MODE

Tools:
  - originba_list_clients()
  - originba_run_readonly_sql(client, sql, max_rows)

Security:
  - SELECT / WITH only (single statement)
  - SET TRANSACTION READ ONLY before every query
  - row cap (default 500, hard max 5000)
  - *_prod clients disabled unless ORIGINBA_MCP_ALLOW_PROD=1
  - never returns passwords or raw DSNs with secrets
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import oracledb
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from oracle_client import ensure_oracle_client, load_env_file, normalize_oracle_dsn
from run_client_oracle_sql import CLIENTS, client_connection

DEFAULT_MAX_ROWS = 500
HARD_MAX_ROWS = 5000
DEFAULT_TIMEOUT_MS = 120_000

# Note: do NOT ban REPLACE — Oracle SQL REPLACE() string function is valid in SELECT.
# CREATE OR REPLACE remains blocked via CREATE.
_FORBIDDEN = re.compile(
    r"(?is)\b("
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT|"
    r"CREATE|ALTER|DROP|TRUNCATE|RENAME|GRANT|REVOKE|"
    r"EXECUTE|EXEC|CALL|BEGIN|DECLARE|ANONYMOUS|"
    r"COMMIT|ROLLBACK|SAVEPOINT|"
    r"LOCK|ANALYZE|AUDIT|COMMENT|FLASHBACK|PURGE|"
    r"DBMS_|UTL_"
    r")\b"
)
_FOR_UPDATE = re.compile(r"(?is)\bFOR\s+UPDATE\b")
_LEADING = re.compile(r"(?is)^\s*(WITH|SELECT)\b")

server = Server("originba-oracle")


def _env_path() -> Path:
    override = os.environ.get("ORIGINBA_ENV_PATH") or os.environ.get("ORIGINBA_DOTENV")
    if override:
        return Path(override).expanduser().resolve()
    return REPO_ROOT / ".env"


def _allow_prod() -> bool:
    return (os.environ.get("ORIGINBA_MCP_ALLOW_PROD") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def _non_prod_clients() -> list[str]:
    return sorted(c for c in CLIENTS if not c.endswith("_prod") or _allow_prod())


def validate_readonly_sql(sql: str) -> str:
    text = (sql or "").strip()
    if not text:
        raise ValueError("SQL is empty.")
    if ";" in text.rstrip(";"):
        raise ValueError("Only a single SQL statement is allowed (no internal semicolons).")
    text = text.rstrip().rstrip(";").strip()
    if not _LEADING.match(text):
        raise ValueError("SQL must start with SELECT or WITH.")
    if _FORBIDDEN.search(text):
        raise ValueError("SQL contains a forbidden keyword (DML/DDL/PLSQL).")
    if _FOR_UPDATE.search(text):
        raise ValueError("FOR UPDATE is not allowed.")
    before_from = text.upper().split("FROM", 1)[0]
    if before_from.strip().upper().startswith("SELECT") and "INTO" in before_from:
        raise ValueError("SELECT INTO is not allowed.")
    return text


def _sanitize_error(exc: BaseException) -> str:
    msg = str(exc)
    msg = re.sub(r"(?i)password\s*=\s*\S+", "password=***", msg)
    return msg[:800]


def _load_config() -> dict[str, str]:
    env_path = _env_path()
    if not env_path.is_file():
        raise FileNotFoundError(f".env not found at {env_path}")
    return load_env_file(env_path)


def list_clients_payload() -> dict[str, Any]:
    return {
        "allowed_clients": _non_prod_clients(),
        "prod_enabled": _allow_prod(),
        "env_path": str(_env_path()),
        "notes": [
            "Use int_dev for Origin DEV baseline.",
            "Use ellensburg/newark/etc for SmartCity TEST clients.",
            "Connect user is CPOWERS (not JRS2C2M).",
            "VPN must be up on this Mac.",
        ],
    }


def run_readonly_sql(client: str, sql: str, max_rows: int = DEFAULT_MAX_ROWS) -> dict[str, Any]:
    client = (client or "").strip().lower()
    if client not in CLIENTS:
        raise ValueError(f"Unknown client {client!r}. Call originba_list_clients().")
    if client.endswith("_prod") and not _allow_prod():
        raise ValueError("Production clients are disabled. Set ORIGINBA_MCP_ALLOW_PROD=1 to enable.")

    safe_sql = validate_readonly_sql(sql)
    rows_cap = max(1, min(int(max_rows or DEFAULT_MAX_ROWS), HARD_MAX_ROWS))

    config = _load_config()
    ensure_oracle_client(config)
    user, password, dsn = client_connection(config, client)
    timeout_ms = int(
        os.environ.get("ORIGINBA_MCP_TIMEOUT_MS")
        or config.get("DB_CALL_TIMEOUT_MS")
        or DEFAULT_TIMEOUT_MS
    )
    if not os.environ.get("ORIGINBA_MCP_TIMEOUT_MS") and timeout_ms > DEFAULT_TIMEOUT_MS:
        timeout_ms = DEFAULT_TIMEOUT_MS

    with oracledb.connect(
        user=user,
        password=password,
        dsn=normalize_oracle_dsn(dsn),
    ) as conn:
        conn.call_timeout = timeout_ms
        with conn.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute(safe_sql)
            if cursor.description is None:
                return {
                    "client": client,
                    "connected_user": user,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "truncated": False,
                    "max_rows": rows_cap,
                }
            columns = [col[0] for col in cursor.description]
            fetched = cursor.fetchmany(rows_cap)
            rows: list[dict[str, Any]] = []
            for tup in fetched:
                row: dict[str, Any] = {}
                for i, v in enumerate(tup):
                    if v is None or isinstance(v, (int, float, str, bool)):
                        row[columns[i]] = v
                    else:
                        row[columns[i]] = str(v)
                rows.append(row)
            return {
                "client": client,
                "connected_user": user,
                "columns": columns,
                "row_count": len(rows),
                "truncated": len(fetched) == rows_cap,
                "max_rows": rows_cap,
                "rows": rows,
            }


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="originba_list_clients",
            description="List allowed OriginBA Oracle client aliases for read-only queries.",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="originba_run_readonly_sql",
            description=(
                "Run a single read-only SELECT/WITH against a named OriginBA client "
                "(int_dev, ellensburg, newark, ...). VPN required. Uses CPOWERS path."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "client": {
                        "type": "string",
                        "description": "Client alias from originba_list_clients.",
                    },
                    "sql": {
                        "type": "string",
                        "description": "One SELECT or WITH statement.",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Row cap (default 500, hard max 5000).",
                        "default": DEFAULT_MAX_ROWS,
                        "minimum": 1,
                        "maximum": HARD_MAX_ROWS,
                    },
                },
                "required": ["client", "sql"],
                "additionalProperties": False,
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    try:
        if name == "originba_list_clients":
            payload = list_clients_payload()
        elif name == "originba_run_readonly_sql":
            payload = run_readonly_sql(
                client=str(args.get("client") or ""),
                sql=str(args.get("sql") or ""),
                max_rows=int(args.get("max_rows") or DEFAULT_MAX_ROWS),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        return [TextContent(type="text", text=json.dumps(payload, indent=2, default=str))]
    except Exception as exc:  # noqa: BLE001
        return [TextContent(type="text", text=json.dumps({"error": _sanitize_error(exc)}, indent=2))]


async def _amain() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="originba-oracle",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def _self_test_guards() -> None:
    cases = [
        ("SELECT 1 FROM dual", True),
        ("WITH x AS (SELECT 1 a FROM dual) SELECT * FROM x", True),
        ("SELECT created_dt, update_dttm FROM cisadm.ci_ft WHERE ROWNUM=1", True),
        ("SELECT REPLACE(descr,'-',' ') AS d FROM cisadm.ci_sa_type_l WHERE ROWNUM=1", True),
        ("DELETE FROM cisadm.ci_ft", False),
        ("DROP TABLE x", False),
        ("SELECT 1 FROM dual; SELECT 2 FROM dual", False),
        ("SELECT * FROM cisadm.ci_ft FOR UPDATE", False),
        ("BEGIN NULL; END;", False),
    ]
    for sql, ok in cases:
        try:
            validate_readonly_sql(sql)
            assert ok, f"expected reject: {sql}"
        except ValueError:
            assert not ok, f"expected allow: {sql}"


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test_guards()
        print("originba_oracle_mcp guard self-test: PASS")
        raise SystemExit(0)
    asyncio.run(_amain())
