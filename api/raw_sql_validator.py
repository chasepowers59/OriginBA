"""
Validate demo-only read-only SQL against a single governed snapshot table.

Scope is checked by PARSING the FROM/JOIN targets, not by looking for the table's
name somewhere in the text. The old substring test was satisfied by a comment, so a
statement could read any table it liked as long as it mentioned the allowed one
(audit H3); it also applied no secrets guard and none of the Oracle escape-hatch
rules the SQL workspace enforces. Both now come from sql_workspace_validator, so
"protected column" and "escape hatch" have one definition across the two paths.
"""

from __future__ import annotations

import re

from api.sql_workspace_validator import (
    SqlWorkspaceValidationError,
    enforce_oracle_hatches,
    enforce_secrets,
    strip_sql_noise,
)


class RawSqlValidationError(ValueError):
    pass


_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.IGNORECASE,
)

# Every table the statement reads: FROM/JOIN, optionally schema-qualified. Run over
# the cleaned text so a comment or string literal cannot hide one.
_READ_TARGETS = re.compile(
    r'\b(?:FROM|JOIN)\s+("?[\w$#]+"?)(?:\s*\.\s*("?[\w$#]+"?))?',
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
    scanned = strip_sql_noise(cleaned)

    try:
        enforce_oracle_hatches(scanned)
        enforce_secrets(scanned)
    except SqlWorkspaceValidationError as exc:
        raise RawSqlValidationError(str(exc)) from exc

    targets = []
    for qualifier, name in _READ_TARGETS.findall(scanned):
        schema = qualifier.strip('"').upper() if name else ""
        targets.append((schema, (name or qualifier).strip('"').upper()))

    if not targets:
        raise RawSqlValidationError(f"Query must read CISADM.{table}")

    for schema, target in targets:
        if target != table or schema not in ("", "CISADM"):
            named = f"{schema}.{target}" if schema else target
            raise RawSqlValidationError(
                f"This query is scoped to CISADM.{table} -- '{named}' is not readable here."
            )

    return cleaned


def apply_row_cap(sql: str, limit: int) -> str:
    cap = max(1, min(limit, 500))
    upper = sql.upper()
    if "ROWNUM" in upper or "FETCH FIRST" in upper or "FETCH NEXT" in upper:
        return sql
    return f"SELECT * FROM ({sql}) snapshot_q WHERE ROWNUM <= {cap}"
