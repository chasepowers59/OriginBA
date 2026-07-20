"""
Validate read-only SQL for the portal database workspace.

Broader than snapshot-scoped raw SQL: any SELECT against the connected database,
still single-statement and read-only.
"""

from __future__ import annotations

import re


class SqlWorkspaceValidationError(ValueError):
    pass


_FORBIDDEN = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|MERGE|UPSERT|"
    r"DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|"
    r"EXEC|EXECUTE|CALL|BEGIN|DECLARE|"
    r"COMMIT|ROLLBACK|SAVEPOINT|"
    r"LOCK|UNLOCK|ANALYZE|AUDIT|NOAUDIT|"
    r"PURGE|RENAME|COMMENT|ASSOCIATE|DISASSOCIATE"
    r")\b",
    re.IGNORECASE,
)

_FOR_UPDATE = re.compile(r"\bFOR\s+UPDATE\b", re.IGNORECASE)
_INTO_CLAUSE = re.compile(r"\bSELECT\b.+\bINTO\b", re.IGNORECASE | re.DOTALL)


def validate_workspace_sql(sql: str) -> str:
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise SqlWorkspaceValidationError("SQL is empty")

    if not cleaned.upper().startswith("SELECT") and not cleaned.upper().startswith("WITH"):
        raise SqlWorkspaceValidationError("Only SELECT statements (including WITH/CTE) are allowed")

    if ";" in cleaned:
        raise SqlWorkspaceValidationError("Multiple statements are not allowed")

    if _FORBIDDEN.search(cleaned):
        raise SqlWorkspaceValidationError("Statement contains forbidden keywords")

    if _FOR_UPDATE.search(cleaned):
        raise SqlWorkspaceValidationError("FOR UPDATE is not allowed")

    if _INTO_CLAUSE.search(cleaned):
        raise SqlWorkspaceValidationError("SELECT INTO is not allowed")

    return cleaned


def wrap_paginated_sql(sql: str, *, offset: int, limit: int, probe_extra: int = 0) -> str:
    """Wrap user SQL with OFFSET/FETCH for SQL-Developer-style paging."""
    off = max(0, offset)
    lim = max(1, min(limit, 500))
    fetch = lim + max(0, min(probe_extra, 1))
    return (
        f"SELECT * FROM (\n{sql}\n) PORTAL_SQL_WS "
        f"OFFSET {off} ROWS FETCH NEXT {fetch} ROWS ONLY"
    )


def wrap_count_sql(sql: str) -> str:
    return f"SELECT COUNT(*) AS PORTAL_ROW_COUNT FROM (\n{sql}\n) PORTAL_COUNT_Q"
