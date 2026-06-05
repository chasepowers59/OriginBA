#!/usr/bin/env python3
"""
Run Oracle SQL against a named SmartCity client from local .env aliases.

This runner supports the repo deployment wrappers that use SQL*Plus-style
@@ includes, so the same deployment_steps scripts can be run from this Mac.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import oracledb
from dotenv import dotenv_values


CLIENTS = {
    "newark": "NEWARK",
    "fonddulac": "FONDDULAC",
    "collegestation": "COLLEGESTATION",
    "ellensburg": "ELLENSBURG",
    "citycorp": "CITYCORP",
    "demo": "DEMO",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Oracle SQL against a named SmartCity client.")
    parser.add_argument("--client", choices=sorted(CLIENTS), required=True)
    parser.add_argument("--file", help="SQL file to execute.")
    parser.add_argument("--sql", help="Inline SQL to execute.")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--max-rows", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true", help="Resolve includes and print statement count only.")
    parser.add_argument(
        "--fail-if-any-rows",
        action="store_true",
        help="Exit with code 1 when any SELECT returns one or more rows (for install gate scripts).",
    )
    parser.add_argument(
        "--log-file",
        help="Append full stdout to this file in addition to printing.",
    )
    return parser.parse_args()


def init_oracle_client(config: dict[str, str]) -> None:
    thick_mode = (config.get("DB_THICK_MODE") or "").strip().lower() in {"1", "true", "yes", "y"}
    lib_dir = (config.get("ORACLE_CLIENT_LIB_DIR") or "").strip()
    if thick_mode and lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        except oracledb.ProgrammingError:
            pass


def resolve_include(include_path: str, current_file: Path) -> Path:
    normalized = include_path.strip().replace("\\", "/")
    candidate = (current_file.parent / normalized).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Unable to resolve include {include_path!r} from {current_file}")


def expand_includes(path: Path, seen: set[Path] | None = None) -> str:
    seen = seen or set()
    path = path.resolve()
    if path in seen:
        raise RuntimeError(f"Recursive SQL include detected: {path}")
    seen.add(path)

    expanded_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("@@"):
            include = resolve_include(stripped[2:], path)
            expanded_lines.append(expand_includes(include, seen))
        else:
            expanded_lines.append(line)
    seen.remove(path)
    return "\n".join(expanded_lines)


def split_sql_script(text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    in_plsql_block = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        upper = stripped.upper()

        if not stripped:
            if in_plsql_block:
                buffer.append(raw_line)
            continue
        if stripped.startswith("--"):
            continue
        if upper.startswith("PROMPT"):
            continue
        if upper.startswith("SET ") or upper.startswith("WHENEVER "):
            continue

        starts_plsql = bool(
            re.match(
                r"^(CREATE\s+OR\s+REPLACE\s+(PROCEDURE|FUNCTION|PACKAGE|TRIGGER)|DECLARE|BEGIN)\b",
                upper,
            )
        )
        if starts_plsql and not buffer:
            in_plsql_block = True
            buffer.append(raw_line)
            continue

        if stripped == "/":
            if in_plsql_block:
                statement = "\n".join(buffer).strip()
                if statement:
                    statements.append(statement)
                buffer = []
                in_plsql_block = False
            continue

        buffer.append(raw_line)
        if not in_plsql_block and stripped.endswith(";"):
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


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data: str) -> None:
        for stream in self.streams:
            stream.write(data)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def print_table(columns: list[str], rows: list[tuple]) -> None:
    widths = [len(col) for col in columns]
    string_rows = []
    for row in rows:
        values = ["" if value is None else str(value) for value in row]
        string_rows.append(values)
        for index, value in enumerate(values):
            widths[index] = max(widths[index], len(value))

    def format_row(values: list[str]) -> str:
        return " | ".join(value.ljust(widths[index]) for index, value in enumerate(values))

    print(format_row(columns))
    print("-+-".join("-" * width for width in widths))
    for values in string_rows:
        print(format_row(values))


def load_config(repo_root: Path) -> dict[str, str]:
    values = dotenv_values(repo_root / ".env")
    return {key: value for key, value in values.items() if value is not None}


def client_connection(config: dict[str, str], client: str) -> tuple[str, str, str]:
    prefix = CLIENTS[client]
    user = config.get(f"{prefix}_DB_USER") or config.get("DB_USER") or config.get("ORACLE_USER")
    password = config.get(f"{prefix}_DB_PASSWORD") or config.get("DB_PASSWORD") or config.get("ORACLE_PASSWORD")
    dsn = config.get(f"{prefix}_ORACLE_DSN") or config.get(f"{prefix}_DB_CONNECT_STRING")
    if not user or not password or not dsn:
        raise RuntimeError(f"Missing connection config for client {client}")
    return user, password, dsn


def emit(message: str = "", *, end: str = "\n") -> None:
    print(message, end=end, flush=True)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    config = load_config(repo_root)
    init_oracle_client(config)

    if args.file:
        sql_text = expand_includes(Path(args.file).expanduser().resolve())
    elif args.sql:
        sql_text = args.sql
    else:
        raise RuntimeError("Provide --file or --sql.")

    statements = split_sql_script(sql_text)
    emit(f"Client: {args.client}")
    emit(f"Statements: {len(statements)}")

    if args.dry_run:
        return 0

    log_handle = None
    original_stdout = sys.stdout
    if args.log_file:
        log_path = Path(args.log_file).expanduser().resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        sys.stdout = _Tee(original_stdout, log_handle)

    exit_code = 0
    failure_rows: list[tuple[int, int, list[tuple]]] = []

    try:
        user, password, dsn = client_connection(config, args.client)
        call_timeout_ms = int(
            os.environ.get("DB_CALL_TIMEOUT_MS")
            or config.get("DB_CALL_TIMEOUT_MS")
            or "900000"
        )
        fetch_array_size = int(config.get("DB_FETCH_ARRAY_SIZE") or "200")

        with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
            conn.call_timeout = call_timeout_ms
            with conn.cursor() as cursor:
                cursor.arraysize = fetch_array_size
                for index, sql in enumerate(statements, start=1):
                    emit(f"\n=== Statement {index}/{len(statements)} ===")
                    cursor.execute(sql)
                    if cursor.description is None:
                        emit("Statement executed successfully.")
                        continue

                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchmany(args.max_rows)
                    if args.format == "json":
                        emit(json.dumps([dict(zip(columns, row)) for row in rows], default=str, indent=2))
                    else:
                        print_table(columns, rows)
                    if args.fail_if_any_rows and rows:
                        failure_rows.append((index, len(rows), rows))
    finally:
        if log_handle is not None:
            sys.stdout = original_stdout
            log_handle.close()

    if failure_rows:
        emit("\nVALIDATION GATE FAILED")
        for index, row_count, rows in failure_rows:
            emit(f"- Statement {index}: {row_count} failure row(s)")
            for row in rows[:10]:
                emit(f"  {row}")
        return 1

    if args.fail_if_any_rows:
        emit("\nVALIDATION GATE PASSED")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
