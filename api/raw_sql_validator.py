"""
Validate demo-only read-only SQL against a single governed snapshot table.
"""

from __future__ import annotations

import re


class RawSqlValidationError(ValueError):
    pass


_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)


def validate_raw_sql(sql: str, allowed_table: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise RawSqlValidationError("SQL is empty")

    if not cleaned.upper().startswith("SELECT"):
        raise RawSqlValidationError("Only SELECT statements are allowed")

    if _FORBIDDEN.search(cleaned):
        raise RawSqlValidationError("Statement contains forbidden keywords")

    if ";" in cleaned:
        raise RawSqlValidationError("Multiple statements are not allowed")

    table = allowed_table.upper()
    if f"CISADM.{table}" not in cleaned.upper() and f"cisadm.{table.lower()}" not in cleaned.lower():
        raise RawSqlValidationError(f"Query must reference CISADM.{table}")

    return cleaned


def apply_row_cap(sql: str, limit: int) -> str:
    cap = max(1, min(limit, 500))
    upper = sql.upper()
    if "ROWNUM" in upper or "FETCH FIRST" in upper or "FETCH NEXT" in upper:
        return sql
    return f"SELECT * FROM ({sql}) snapshot_q WHERE ROWNUM <= {cap}"
