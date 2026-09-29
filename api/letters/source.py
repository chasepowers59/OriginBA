"""Raw CISADM reads for a Postgres organization, through the portal's own warehouse connection.

Letters read the raw tables, not the reporting canvases: the canvases deliberately drop names,
addresses and bill totals, and a letter needs all three. Never through execute_query: it stops at
5,000 rows without saying so, and a month of Ellensburg collection events is 23,157. Here every
read streams through a server-side cursor and RAISES past the ceiling, because a letter built from
half its events announces the wrong dates.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterator

from api.sql_workspace_validator import strip_sql_noise, validate_reporting_scope, validate_workspace_sql
from api.warehouse_db import warehouse_connection

SQL_DIR = Path(__file__).resolve().parent / "sql" / "postgres"
ROW_CEILING = 100_000
STATEMENT_TIMEOUT = "60s"


class RowCeilingExceeded(RuntimeError):
    def __init__(self, query: str, ceiling: int):
        super().__init__(f"letters query '{query}' returned more than {ceiling:,} rows")
        self.query, self.ceiling = query, ceiling


@lru_cache(maxsize=None)
def _load(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    # The same fences as the SQL workspace: read-only, one statement, cisadm + reporting only,
    # no protected column. The files are ours, but a later edit must not carry a secret out.
    validate_workspace_sql(strip_sql_noise(text))
    validate_reporting_scope(text)
    return text


def sql(name: str) -> str:
    return _load(SQL_DIR / f"{name}.sql")


class Source:
    def __init__(self, conn: Any, ceiling: int):
        self._conn, self._ceiling = conn, ceiling

    def rows(self, name: str, filter_sql: str, binds: dict[str, Any]) -> list[dict[str, Any]]:
        """Every row of one letters query. `filter_sql` is one of the repository's fixed predicates,
        never request text; every value arrives as a named bind."""
        text = f"/* letters:{name} */\n" + sql(name).replace("{filter}", filter_sql)
        cur = self._conn.cursor(name=f"letters_{name}")
        try:
            cur.execute(text, binds)
            fetched = cur.fetchmany(self._ceiling + 1)
            if len(fetched) > self._ceiling:
                raise RowCeilingExceeded(name, self._ceiling)
            columns = [c[0] for c in cur.description or ()]
            return [dict(zip(columns, r)) for r in fetched]
        finally:
            cur.close()


@contextmanager
def open_source(organization_id: str, *, connection: Callable | None = None,
                ceiling: int = ROW_CEILING) -> Iterator[Source]:
    """One read-only, repeatable-read transaction for every query a request makes, so the list
    and its balances, processes and events describe the same moment."""
    with (connection or warehouse_connection)(organization_id) as conn:
        with conn.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            cur.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
            cur.execute("SET LOCAL search_path = cisadm")
        yield Source(conn, ceiling)
