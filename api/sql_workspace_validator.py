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


# Schemas a WAREHOUSE workspace query may not name. The portal's contract is that end
# users read only the governed reporting canvases -- staging/core are implementation
# layers and cisadm/landing are raw source. Unqualified names are handled separately by
# pinning search_path to reporting, so this only has to catch explicit qualification.
_NON_REPORTING_SCHEMA = re.compile(
    r"\b(cisadm|landing|staging|core|public|pg_catalog|information_schema)\s*\.",
    re.IGNORECASE,
)


def validate_reporting_scope(sql: str) -> None:
    """Reject warehouse SQL that reaches outside the reporting layer."""
    match = _NON_REPORTING_SCHEMA.search(sql)
    if match:
        raise SqlWorkspaceValidationError(
            f"The workspace is scoped to the reporting layer -- "
            f"'{match.group(1)}.' is not queryable here. "
            f"Query the reporting.rpt_* canvases instead."
        )


# The in-database workspace's fence (oracle_dbt shape). The session's
# CURRENT_SCHEMA is pinned to ORIGINBA_REPORTING so unqualified names resolve to
# the governed canvases; this catches explicit qualification elsewhere AND the
# Oracle-specific escape hatches a Postgres deny-list never had to think about:
# dictionary views (all_/dba_/user_/v$/cdb_), PL/SQL package surface (dbms_/utl_),
# XML/network functions, and database links (@).
_ORACLE_NON_REPORTING = re.compile(
    r"\b(cisadm|originba_staging|originba_core|originba_src|sys|system)\s*\.",
    re.IGNORECASE,
)
_ORACLE_DICTIONARY = re.compile(
    r"\b(all_|dba_|user_|cdb_|v\$|gv\$)\w*",
    re.IGNORECASE,
)
_ORACLE_PACKAGES = re.compile(
    r"\b(dbms_|utl_|owa_|htp\.|httpuritype|xmltype|extractvalue|ctxsys)\w*",
    re.IGNORECASE,
)
_ORACLE_DBLINK = re.compile(r"@\w+", re.IGNORECASE)


def validate_oracle_reporting_scope(sql: str) -> None:
    """Reject in-database workspace SQL that reaches outside ORIGINBA_REPORTING."""
    match = _ORACLE_NON_REPORTING.search(sql)
    if match:
        raise SqlWorkspaceValidationError(
            f"The workspace is scoped to the reporting layer -- "
            f"'{match.group(1)}.' is not queryable here. "
            f"Query the rpt_* canvases (unqualified or ORIGINBA_REPORTING.rpt_*)."
        )
    for pattern, what in ((_ORACLE_DICTIONARY, "data dictionary views"),
                          (_ORACLE_PACKAGES, "PL/SQL packages and network functions"),
                          (_ORACLE_DBLINK, "database links")):
        m = pattern.search(sql)
        if m:
            raise SqlWorkspaceValidationError(
                f"{what.capitalize()} are not queryable from the workspace ('{m.group(0)}')."
            )


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
