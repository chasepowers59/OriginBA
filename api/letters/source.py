"""Raw CISADM reads for an organization, through the portal's own connection to it.

Letters read the raw tables, not the reporting canvases: the canvases deliberately drop names,
addresses and bill totals, and a letter needs all three. Never through execute_query: it stops at
5,000 rows without saying so, and a month of Ellensburg collection events is 23,157. Here every
read RAISES past the ceiling, because a letter built from half its events announces the wrong dates.

The organization's engine picks the dialect: a Postgres org reads sql/postgres (unqualified, the
search_path pins cisadm) through its warehouse; an Oracle org reads sql/oracle (CISADM-qualified,
the letter-print app's proven SQL) through its own connection. The SQL files carry `{filter}` and,
for the late fees, `{types}`; every value arrives as a named bind.
"""
from __future__ import annotations

import decimal
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator

from api.demo_db import demo_connection
from api.oracle_client import oracledb
from api.snapshot_catalog import org_backend
from api.sql_workspace_validator import (strip_sql_noise, validate_oracle_reporting_scope,
                                         validate_reporting_scope, validate_workspace_sql)
from api.warehouse_db import warehouse_connection

SQL_ROOT = Path(__file__).resolve().parent / "sql"
ROW_CEILING = 100_000
STATEMENT_TIMEOUT = "60s"
# Per round trip in python-oracledb. Measured on Ellensburg (2026-09-29): the balances query ran 45 s
# and past 60 s on a cold cache (72,664 disk reads over CI_FT) against ~1 s warm.
ORACLE_CALL_TIMEOUT_MS = 120_000
ORACLE_ARRAYSIZE = 5_000            # rows per round trip: a month of events is ~23,000 rows over a VPN

_FENCES = {"postgres": validate_reporting_scope, "oracle": validate_oracle_reporting_scope}


class RowCeilingExceeded(RuntimeError):
    def __init__(self, query: str, ceiling: int):
        super().__init__(f"letters query '{query}' returned more than {ceiling:,} rows")
        self.query, self.ceiling = query, ceiling


class UnsupportedEngine(RuntimeError):
    pass


def dialect_for(organization_id: str) -> str:
    engine, _ = org_backend(organization_id)
    if engine not in _FENCES:
        raise UnsupportedEngine(f"letters do not read a {engine} database")
    return engine


@lru_cache(maxsize=None)
def _load(path: Path, dialect: str) -> str:
    text = path.read_text(encoding="utf-8")
    # The same fences as the SQL workspace: read-only, one statement, CISADM + reporting only,
    # no protected column. The files are ours, but a later edit must not carry a secret out.
    validate_workspace_sql(strip_sql_noise(text))
    _FENCES[dialect](text)
    return text


def sql(name: str, dialect: str) -> str:
    return _load(SQL_ROOT / dialect / f"{name}.sql", dialect)


def _exact_numbers(cursor: Any, metadata: Any) -> Any:
    """python-oracledb returns NUMBER as a float unless asked; an amount owed must stay exact."""
    if metadata.type_code is oracledb.DB_TYPE_NUMBER:
        return cursor.var(decimal.Decimal, arraysize=cursor.arraysize)
    return None


class Source:
    def __init__(self, conn: Any, ceiling: int, dialect: str):
        self._conn, self._ceiling, self.dialect = conn, ceiling, dialect

    def _marker(self, key: str) -> str:
        return f":{key}" if self.dialect == "oracle" else f"%({key})s"

    def rows(self, name: str, filter_sql: str, binds: dict[str, Any]) -> list[dict[str, Any]]:
        """Every row of one letters query. `filter_sql` is one of the repository's fixed predicates,
        never request text, with a `{field}` where each bind goes."""
        text = f"/* letters:{name} */\n" + sql(name, self.dialect).replace("{filter}", filter_sql)
        flat: dict[str, Any] = {}
        for key, value in binds.items():
            if isinstance(value, (list, tuple)):    # one marker per element: Oracle binds no array into IN
                keys = [f"{key}_{i}" for i in range(len(value))]
                flat.update(zip(keys, value))
            else:
                keys, flat[key] = [key], value
            text = text.replace("{" + key + "}", ", ".join(self._marker(k) for k in keys))
        if self.dialect == "oracle":
            cur = self._conn.cursor()
            cur.arraysize = cur.prefetchrows = ORACLE_ARRAYSIZE
            cur.outputtypehandler = _exact_numbers
        else:
            cur = self._conn.cursor(name=f"letters_{name}")     # server-side: streamed, not loaded whole
        try:
            cur.execute(text, flat)
            fetched = cur.fetchmany(self._ceiling + 1)
            if len(fetched) > self._ceiling:
                raise RowCeilingExceeded(name, self._ceiling)
            columns = [c[0].lower() for c in cur.description or ()]   # Oracle answers in UPPERCASE
            return [dict(zip(columns, r)) for r in fetched]
        finally:
            cur.close()


@contextmanager
def _postgres(conn: Any) -> Iterator[None]:
    with conn.cursor() as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        cur.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
        cur.execute("SET LOCAL search_path = cisadm")
    yield


@contextmanager
def _oracle(conn: Any) -> Iterator[None]:
    # A READ ONLY transaction sees one moment for every query in it and refuses any write. The
    # session is pooled and shared, so nothing about it changes but the call timeout, restored after.
    previous = conn.call_timeout
    conn.call_timeout = ORACLE_CALL_TIMEOUT_MS
    try:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION READ ONLY")
        yield
    finally:
        conn.call_timeout = previous


_CONNECT = {"postgres": (warehouse_connection, _postgres), "oracle": (demo_connection, _oracle)}


@contextmanager
def open_source(organization_id: str, *, connection: Callable | None = None,
                ceiling: int = ROW_CEILING) -> Iterator[Source]:
    """One read-only transaction for every query a request makes, so the list and its balances,
    processes and events describe the same moment."""
    dialect = dialect_for(organization_id)
    connect, begin = _CONNECT[dialect]
    with (connection or connect)(organization_id) as conn, begin(conn):
        yield Source(conn, ceiling, dialect)
