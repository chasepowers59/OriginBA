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


# ---------------------------------------------------------------------------
# Scope fencing for the ad-hoc workspace.
#
# The workspace pins the session default schema (Postgres search_path / Oracle
# CURRENT_SCHEMA) to the reporting layer, so an UNQUALIFIED name resolves to a
# governed canvas. These validators exist to stop an EXPLICIT qualifier reaching
# another schema. A regex deny-list alone is not enough (2026-08-28 security
# review): `"CISADM"."CI_ACCT"` and `CISADM/**/.CI_ACCT` both slip past a naive
# `\bcisadm\s*\.` because a quote or a comment sits between the name and the dot.
# The model here is defense in depth:
#   A. strip comments and string literals first (a literal or comment can hide
#      a qualifier, and its contents must never be scanned as code);
#   B. a POSITIVE allow-list on FROM/JOIN-position qualifiers -- the only schema
#      a table may be qualified with is the reporting schema, so an UNKNOWN
#      other schema is rejected too, not only the enumerated ones;
#   C. reject any quoted identifier used as a schema qualifier outright
#      (a reporting query never needs "SCHEMA".table -- tables are unquoted
#      rpt_*), which closes the quoted-qualifier class wholesale;
#   D. the original deny-list, on the cleaned text, as a backstop for comma-join
#      position and the Oracle-specific escape hatches.
# The primary boundary remains the DATABASE GRANT: the workspace connection
# should hold SELECT only on the reporting schema (see oracle-native-rollout).
# ---------------------------------------------------------------------------

_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"--[^\n]*")
_STRING_LITERAL = re.compile(r"'(?:[^']|'')*'")
# A quoted identifier ("...") immediately before a dot == a quoted schema
# qualifier. A quoted COLUMN sits AFTER a dot (t."Col") or standalone, so this
# does not touch legitimate quoted column names.
_QUOTED_QUALIFIER = re.compile(r'"[^"]*"\s*\.')
# schema.table in FROM/JOIN position, qualifier captured (quoted or bare).
_FROM_JOIN_QUALIFIER = re.compile(
    r'\b(?:FROM|JOIN)\s+("?[A-Za-z_$#][\w$#]*"?)\s*\.',
    re.IGNORECASE,
)


def strip_sql_noise(sql: str) -> str:
    """Remove comments and string literals so the scope scan sees only code."""
    cleaned = _BLOCK_COMMENT.sub(" ", sql)
    cleaned = _LINE_COMMENT.sub(" ", cleaned)
    cleaned = _STRING_LITERAL.sub("''", cleaned)
    return cleaned


# ---------------------------------------------------------------------------
# Secrets guard (2026-08-31): CISADM is queryable — utility analysts know the
# CIS schema, and it is what the workspace is FOR — but the columns that hold
# secrets never are. MICR_ID is bank routing, WEB_PASSWD* are credentials,
# ALERT_INFO is free-text operational notes. Two layers:
#   1. any mention of a secret column name is rejected outright;
#   2. SELECT * against any table that carries one is rejected — an explicit
#      column list is required there instead;
#   3. whole-row projection of such a table (row_to_json(t), t::text) is
#      rejected, because it returns the value without naming the column.
# ---------------------------------------------------------------------------
_SECRET_COLUMNS = re.compile(r"\b(micr_id|web_passwd\w*|alert_info)\b", re.IGNORECASE)

# Every CISADM table that carries one of those columns. Naming the column is not
# the only way to read it: `SELECT *` and whole-row projection both return it
# without ever mentioning it (audit C4), so the guard is per TABLE, not per name.
_SECRET_TABLES = ("ci_pay_tndr", "ci_per", "ci_acct", "ci_acct_apay")
_TABLE_ALT = "|".join(_SECRET_TABLES)

_STAR_ON_SECRET_TABLE = re.compile(
    r"\bSELECT\b[^;]*?(?:^|[\s,(])(?:[\w$#]+\s*\.\s*)?\*.*?\bFROM\b[^;]*?"
    rf"\b(?:{_TABLE_ALT})\b",
    re.IGNORECASE | re.DOTALL,
)

# A bare alias fed to a row-composite function or cast returns the WHOLE row as a
# value: row_to_json(t), to_jsonb(t), t::text, CAST(t AS text). Matched against
# the alias the statement actually binds to a secret-bearing table, so the same
# expression over a harmless table stays allowed.
_ROW_COMPOSITE = re.compile(
    r"(?:\b(?:row_to_json|to_jsonb|to_json|row|hstore)\s*\(\s*(?P<fn>[\w$#]+)\s*\)"
    r"|\b(?P<cast>[\w$#]+)\s*::\s*(?:text|varchar|json|jsonb)\b"
    r"|\bCAST\s*\(\s*(?P<cast2>[\w$#]+)\s+AS\s+(?:text|varchar|json|jsonb)\s*\))",
    re.IGNORECASE,
)
# FROM/JOIN cisadm.ci_per p  ->  {"p": "ci_per", "ci_per": "ci_per"}
_TABLE_ALIAS = re.compile(
    rf"\b(?:FROM|JOIN)\s+(?:[\w$#]+\s*\.\s*)?(?P<table>[\w$#]+)"
    r"(?:\s+(?:AS\s+)?(?P<alias>[A-Za-z_$#][\w$#]*))?",
    re.IGNORECASE,
)
_ALIAS_STOPWORDS = {"where", "group", "order", "having", "join", "on", "limit",
                    "fetch", "offset", "union", "left", "right", "inner", "outer",
                    "cross", "full", "using", "and", "or", "as", "start", "connect"}


def _secret_bearing_names(cleaned: str) -> set[str]:
    """Aliases (and bare table names) in this statement that resolve to a table
    carrying a protected column."""
    names: set[str] = set()
    for m in _TABLE_ALIAS.finditer(cleaned):
        table = m.group("table").lower()
        if table not in _SECRET_TABLES:
            continue
        names.add(table)
        alias = (m.group("alias") or "").lower()
        if alias and alias not in _ALIAS_STOPWORDS:
            names.add(alias)
    return names


def enforce_secrets(cleaned: str) -> None:
    m = _SECRET_COLUMNS.search(cleaned)
    if m:
        raise SqlWorkspaceValidationError(
            f"'{m.group(1)}' is a protected column (secrets never leave the "
            "database). Select the columns you need explicitly, without it."
        )
    if _STAR_ON_SECRET_TABLE.search(cleaned):
        raise SqlWorkspaceValidationError(
            "SELECT * is not allowed on tables that carry protected columns "
            f"({', '.join(t.upper() for t in _SECRET_TABLES)}). List the columns "
            "you need explicitly."
        )
    secret_names = _secret_bearing_names(cleaned)
    if secret_names:
        for m in _ROW_COMPOSITE.finditer(cleaned):
            target = (m.group("fn") or m.group("cast") or m.group("cast2") or "").lower()
            if target in secret_names:
                raise SqlWorkspaceValidationError(
                    "Projecting a whole row from a table with protected columns "
                    f"('{m.group(0).strip()}') is not allowed — it returns the "
                    "protected values without naming them. Select columns explicitly."
                )


def _enforce_scope(sql: str, allowed_schemas: tuple[str, ...], deny: re.Pattern,
                   extra: tuple[tuple[re.Pattern, str], ...] = ()) -> None:
    cleaned = strip_sql_noise(sql)
    primary = allowed_schemas[0]
    allowed = {s.lower() for s in allowed_schemas}

    # C. No quoted schema qualifier at all.
    if _QUOTED_QUALIFIER.search(cleaned):
        raise SqlWorkspaceValidationError(
            "Quoted schema qualifiers are not allowed. Query tables "
            f"unqualified or with the {primary} schema, unquoted."
        )

    # B. Positive allow-list: any FROM/JOIN-qualified table must name an
    #    allowed schema and nothing else -- unknown schemas rejected too.
    for m in _FROM_JOIN_QUALIFIER.finditer(cleaned):
        qualifier = m.group(1).strip('"').lower()
        if qualifier not in allowed:
            raise SqlWorkspaceValidationError(
                f"The workspace is scoped to {', '.join(allowed_schemas)} -- "
                f"'{m.group(1)}.' is not queryable here."
            )

    # D. Deny-list backstop (comma-join position, Oracle escape hatches).
    match = deny.search(cleaned)
    if match:
        raise SqlWorkspaceValidationError(
            f"The workspace is scoped to {', '.join(allowed_schemas)} -- "
            f"'{match.group(1)}.' is not queryable here."
        )
    for pattern, what in extra:
        m = pattern.search(cleaned)
        if m:
            raise SqlWorkspaceValidationError(
                f"{what.capitalize()} are not queryable from the workspace "
                f"('{m.group(0)}')."
            )

    enforce_secrets(cleaned)


_NON_REPORTING_SCHEMA = re.compile(
    r"\b(landing|staging|core|public|pg_catalog|information_schema)\s*\.",
    re.IGNORECASE,
)


# The catalog is reachable WITHOUT its qualifier -- `pg_class`, `pg_database` -- so a
# rule that only matched `pg_catalog.` was bypassed by dropping four characters
# (audit M1). `pg_database` alone enumerates every other client's database name.
# Bounded on both sides so one of our own columns ("Page Count") never trips it.
_PG_CATALOG_OBJECT = re.compile(
    r"(?<![\w.])(pg_(?:class|database|stat_activity|stat_\w+|user|users|shadow|roles|"
    r"authid|settings|namespace|tables|attribute|proc|type|index|indexes|locks|"
    r"available_extensions|extension|catalog|tablespace|largeobject|"
    r"description|depend|constraint|rewrite|trigger|policy|foreign_\w+)|"
    r"information_schema)\b",
    re.IGNORECASE,
)

# Functions that leave the database or hold the connection open: remote links, file
# reads, large-object import, sleeps. The Oracle fence has had its equivalent
# (utl_http, dbms_*) since day one; the Postgres side had none (audit M2).
_PG_DANGEROUS_FUNCTION = re.compile(
    r"\b(dblink\w*|postgres_fdw\w*|pg_read_file|pg_read_binary_file|pg_ls_\w+|"
    r"pg_stat_file|lo_import|lo_export|pg_sleep\w*|pg_terminate_backend|"
    r"pg_cancel_backend|pg_reload_conf|pg_logical_\w+|pg_execute_\w+)\s*\(",
    re.IGNORECASE,
)


def validate_reporting_scope(sql: str) -> None:
    """Reject Postgres warehouse SQL that reaches outside cisadm + reporting.

    CISADM is the workspace's primary surface (analysts know the CIS schema);
    the reporting layer stays queryable for governed canvases. Secrets are
    guarded separately (see enforce_secrets).
    """
    _enforce_scope(
        sql, ("cisadm", "reporting"), _NON_REPORTING_SCHEMA,
        extra=((_PG_CATALOG_OBJECT, "system catalog objects"),
               (_PG_DANGEROUS_FUNCTION, "system and remote-access functions")),
    )


# The in-database (oracle_dbt) fence adds the Oracle-specific escape hatches a
# Postgres deny-list never had to think about: dictionary views
# (all_/dba_/user_/v$/cdb_), PL/SQL package surface (dbms_/utl_), XML/network
# functions, and database links (@).
_ORACLE_NON_REPORTING = re.compile(
    r"\b(originba_staging|originba_core|originba_src|sys|system)\s*\.",
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


_ORACLE_EXTRA = (
    (_ORACLE_DICTIONARY, "data dictionary views"),
    (_ORACLE_PACKAGES, "PL/SQL packages and network functions"),
    (_ORACLE_DBLINK, "database links"),
)


def enforce_oracle_hatches(cleaned: str) -> None:
    """Dictionary views, PL/SQL packages and database links, on already-cleaned text."""
    for pattern, what in _ORACLE_EXTRA:
        m = pattern.search(cleaned)
        if m:
            raise SqlWorkspaceValidationError(
                f"{what.capitalize()} are not queryable from the workspace "
                f"('{m.group(0)}')."
            )


def validate_oracle_reporting_scope(sql: str) -> None:
    """Reject in-database workspace SQL outside CISADM + ORIGINBA_REPORTING.

    CISADM is queryable (it is the schema utility analysts actually know); the
    Oracle escape hatches (dictionary views, PL/SQL, dblinks) and the internal
    build schemas stay fenced, and secrets are guarded (see _enforce_secrets).
    """
    _enforce_scope(sql, ("CISADM", "ORIGINBA_REPORTING"), _ORACLE_NON_REPORTING,
                   extra=_ORACLE_EXTRA)


def validate_oracle_cisadm_scope(sql: str) -> None:
    """Reject legacy-workspace SQL outside CISADM.

    The legacy orgs read their *_RPT_CURR snapshots straight out of CISADM and
    have no ORIGINBA_REPORTING schema, so CISADM is the whole surface. Same
    Oracle escape hatches, same secrets guard.

    This path had NO fence at all until 2026-09-01 (audit C1) — six of eight
    orgs, with `database:sql` held by the lowest role.
    """
    _enforce_scope(sql, ("CISADM",), _ORACLE_NON_REPORTING, extra=_ORACLE_EXTRA)


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
