"""Postgres connection to the dbt reporting warehouse.

WHY THIS SITS BESIDE demo_db.py RATHER THAN REPLACING IT
--------------------------------------------------------
The portal reads two different worlds now. The legacy `*_RPT_CURR` snapshots live in
Oracle CISADM and are reached by demo_db; the dbt canvases live in Postgres and are
reached here. A snapshot's own `schema` says which, so nothing has to be configured twice
and the two can coexist while the migration finishes.

The interface is deliberately the same shape as demo_db.execute_query -- (columns, rows)
-- so the callers choose a backend and change nothing else.

CONNECTION comes from the environment and is never constructed from a request:

    WAREHOUSE_DATABASE_URL              one warehouse for every tenant, or
    WAREHOUSE_DATABASE_URL_<TENANT>     one per client, which is how this project
                                        actually deploys -- dbt builds a separate
                                        database per client, so multi-tenancy here is
                                        ROUTING, not a filter on a column.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "postgres://originba:originba@localhost:5433/originba_training"

_pools: dict[str, Any] = {}


def _env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    # The repo keeps its settings in a root .env; read it rather than requiring the
    # process to be launched with them exported.
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                if k.strip() == name:
                    return v.strip().strip('"').strip("'")
    return None


def warehouse_url(organization_id: str | None = None) -> str:
    if organization_id:
        per_tenant = _env(f"WAREHOUSE_DATABASE_URL_{organization_id.upper()}")
        if per_tenant:
            return per_tenant
    return _env("WAREHOUSE_DATABASE_URL") or DEFAULT_URL


def warehouse_configured(organization_id: str | None = None) -> bool:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        return False
    return bool(warehouse_url(organization_id))


def _pool(organization_id: str | None):
    """One pool per tenant, built on first use and kept.

    Pools are expensive to build and cheap to hold; one per request exhausts the
    server's connection slots long before it exhausts anything here.
    """
    from psycopg2.pool import ThreadedConnectionPool

    url = warehouse_url(organization_id)
    if url not in _pools:
        _pools[url] = ThreadedConnectionPool(1, 8, dsn=url)
    return _pools[url]


@contextmanager
def warehouse_connection(organization_id: str | None = None) -> Iterator[Any]:
    pool = _pool(organization_id)
    conn = pool.getconn()
    try:
        yield conn
    finally:
        # Rolled back, never committed: this path issues SELECT only, and returning a
        # connection mid-transaction leaves the next borrower inside it.
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        pool.putconn(conn)


def execute_query(
    sql: str,
    binds: dict[str, Any] | None = None,
    *,
    organization_id: str | None = None,
    max_rows: int = 5000,
) -> tuple[list[str], list[list[Any]]]:
    binds = binds or {}
    with warehouse_connection(organization_id) as conn:
        with conn.cursor() as cur:
            # A hard server-side ceiling as well as the LIMIT the builder writes: a
            # governed portal must not be able to hold a client warehouse open on one
            # badly-shaped request.
            cur.execute("SET LOCAL statement_timeout = '30s'")
            cur.execute(sql, binds)
            if cur.description is None:
                return [], []
            columns = [c[0] for c in cur.description]
            rows = cur.fetchmany(max_rows)
            return columns, [list(r) for r in rows]


def connection_info(organization_id: str | None = None) -> dict[str, Any]:
    """Masked, for the settings page. Never returns a password."""
    url = warehouse_url(organization_id)
    masked = url
    if "@" in url and "//" in url:
        head, _, tail = url.partition("//")
        creds, _, host = tail.partition("@")
        user = creds.split(":")[0]
        masked = f"{head}//{user}:***@{host}"
    return {"engine": "postgres", "url_masked": masked,
            "configured": warehouse_configured(organization_id)}
