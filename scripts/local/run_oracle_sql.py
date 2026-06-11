import argparse
import json
import os
import sys
from pathlib import Path

import oracledb

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from oracle_client import ensure_oracle_client, load_env_file, normalize_oracle_dsn


def build_connect_string() -> str:
    connect_string = os.getenv("DB_CONNECT_STRING", "").strip()
    if connect_string:
        return connect_string

    host = os.getenv("DB_HOST", "").strip()
    port = os.getenv("DB_PORT", "").strip()
    service_name = os.getenv("DB_SERVICE_NAME", "").strip()

    if host and port and service_name:
        return f"{host}:{port}/{service_name}"

    oracle_dsn = os.getenv("ORACLE_DSN", "").strip()
    if oracle_dsn:
        return oracle_dsn

    raise RuntimeError(
        "No connect string found. Set DB_CONNECT_STRING or DB_HOST/DB_PORT/DB_SERVICE_NAME in .env."
    )


def init_oracle_client() -> None:
    ensure_oracle_client(load_env_file(ROOT / ".env"))


def split_sql_script(text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_create_block = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if not stripped:
            if in_create_block:
                buffer.append(raw_line)
            continue
        if stripped.startswith("--"):
            continue
        if stripped.upper().startswith("PROMPT"):
            continue

        upper = stripped.upper()
        if upper.startswith("CREATE OR REPLACE PROCEDURE") or upper.startswith("CREATE OR REPLACE FUNCTION"):
            in_create_block = True
            buffer.append(raw_line)
            continue

        if stripped == "/":
            if in_create_block:
                statement = "\n".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
                in_create_block = False
            continue

        buffer.append(raw_line)
        if not in_create_block and stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement.endswith(";"):
                statement = statement[:-1].rstrip()
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = "\n".join(buffer).strip()
        if statement.endswith(";"):
            statement = statement[:-1].rstrip()
        if statement:
            statements.append(statement)

    return statements


def load_sql_statements(args: argparse.Namespace) -> list[str]:
    if args.sql:
        return [args.sql.strip().rstrip(";")]
    if args.file:
        return split_sql_script(Path(args.file).read_text(encoding="utf-8"))
    raise RuntimeError("Provide either --sql or --file.")


def print_table(columns: list[str], rows: list[tuple]) -> None:
    widths = [len(col) for col in columns]
    string_rows = []
    for row in rows:
        values = ["" if value is None else str(value) for value in row]
        string_rows.append(values)
        for i, value in enumerate(values):
            widths[i] = max(widths[i], len(value))

    def format_row(values):
        return " | ".join(value.ljust(widths[i]) for i, value in enumerate(values))

    print(format_row(columns))
    print("-+-".join("-" * width for width in widths))
    for values in string_rows:
        print(format_row(values))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Oracle SQL using local .env connection settings.")
    parser.add_argument("--sql", help="Inline SQL to execute.")
    parser.add_argument("--file", help="Path to a .sql file to execute.")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=int(os.getenv("DB_MAX_ROWS", "5000")),
        help="Maximum rows to fetch.",
    )
    args = parser.parse_args()

    config = load_env_file(ROOT / ".env")
    init_oracle_client()

    user = config.get("DB_USER") or config.get("ORACLE_USER")
    password = config.get("DB_PASSWORD") or config.get("ORACLE_PASSWORD")
    dsn = normalize_oracle_dsn(
        config.get("DB_CONNECT_STRING")
        or config.get("ORACLE_DSN")
        or build_connect_string()
    )
    call_timeout_ms = int(config.get("DB_CALL_TIMEOUT_MS") or "120000")
    fetch_array_size = int(config.get("DB_FETCH_ARRAY_SIZE") or "200")

    if not user or not password:
        raise RuntimeError("DB_USER/DB_PASSWORD or ORACLE_USER/ORACLE_PASSWORD must be set in .env.")

    statements = load_sql_statements(args)

    with oracledb.connect(user=user, password=password, dsn=normalize_oracle_dsn(dsn)) as conn:
        conn.call_timeout = call_timeout_ms
        with conn.cursor() as cursor:
            cursor.arraysize = fetch_array_size
            for index, sql in enumerate(statements, start=1):
                if len(statements) > 1:
                    print(f"\n=== Statement {index} ===")

                cursor.execute(sql)

                if cursor.description is None:
                    print("Statement executed successfully.")
                    continue

                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(args.max_rows)

                if args.format == "json":
                    print(json.dumps([dict(zip(columns, row)) for row in rows], default=str, indent=2))
                else:
                    print_table(columns, rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
