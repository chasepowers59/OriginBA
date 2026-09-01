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

import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from api.snapshot_catalog import org_backend

ROOT = Path(__file__).resolve().parent.parent

# The ONLY org allowed to use the unsuffixed WAREHOUSE_DATABASE_URL. Everything
# else must name its own key. A shared default is a cross-client data leak: with
# only the global key set (the shipped render.yaml), every org resolved the same
# database and warehouse_configured() could never say no (audit C2).
SHARED_WAREHOUSE_ORGS = frozenset({"dev"})

_pools: dict[str, Any] = {}

logger = logging.getLogger(__name__)

# A whole KEY=value line pasted into a dashboard's value box. psycopg2 then reports
# `invalid dsn: invalid connection option "WAREHOUSE_DATABASE_URL_DEMO25"`, which
# names the variable and says nothing about the actual mistake. A DSN can never
# legitimately start with a bare KEY=, so strip it -- and warn, because the
# environment is still wrong even though the connection now works.
_PASTED_KEY_PREFIX = re.compile(r"^\s*[A-Z][A-Z0-9_]*\s*=\s*(?=postgres)")


def _clean_url(value: str | None, source: str) -> str | None:
    if not value:
        return None
    cleaned = _PASTED_KEY_PREFIX.sub("", value.strip()).strip().strip('"').strip("'")
    if cleaned != value.strip():
        logger.warning(
            "%s looks like a whole KEY=value line: its value began with the variable "
            "name. Using the URL after the '='; fix the value to start with "
            "'postgresql://'.", source)
    return cleaned or None


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


def warehouse_url(organization_id: str | None = None) -> str | None:
    """This org's Postgres warehouse, or None when it has none.

    None is the honest answer for an Oracle-backed org (demo_db serves those), for
    an unknown org, and for a client whose own key is unset — never another
    tenant's database.
    """
    if organization_id:
        engine, _ = org_backend(organization_id)
        if engine != "postgres":
            return None
        key = f"WAREHOUSE_DATABASE_URL_{organization_id.upper()}"
        per_tenant = _clean_url(_env(key), key)
        if per_tenant:
            return per_tenant
        if organization_id.lower() not in SHARED_WAREHOUSE_ORGS:
            return None
    return _clean_url(_env("WAREHOUSE_DATABASE_URL"), "WAREHOUSE_DATABASE_URL")


def warehouse_configured(organization_id: str | None = None) -> bool:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        return False
    return bool(warehouse_url(organization_id))


def _pool_max() -> int:
    """Max warehouse connections per tenant pool.

    The executive dashboard fans out up to 8 KPI queries at once, and the home page
    issues other warehouse reads (metrics, trends) alongside them; a ceiling of 8 left
    no headroom, so concurrent borrowers hit "connection pool exhausted". Default 16
    gives room above the dashboard fan-out; tune per deployment (a shared transaction
    pooler may want it lower) via WAREHOUSE_POOL_MAX.
    """
    raw = os.environ.get("WAREHOUSE_POOL_MAX") or (_env("WAREHOUSE_POOL_MAX") or "")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 16
    return max(4, value)


def _pool(organization_id: str | None):
    """One pool per tenant, built on first use and kept.

    Pools are expensive to build and cheap to hold; one per request exhausts the
    server's connection slots long before it exhausts anything here.
    """
    from psycopg2.pool import ThreadedConnectionPool

    url = warehouse_url(organization_id)
    if not url:
        # psycopg2 with dsn=None falls back to libpq defaults — another way to land
        # on the wrong database. An org with no warehouse gets an error, not a guess.
        raise RuntimeError(
            f"No warehouse is configured for organization '{organization_id}'. "
            f"Set WAREHOUSE_DATABASE_URL_{(organization_id or '').upper()}."
        )
    if url not in _pools:
        _pools[url] = ThreadedConnectionPool(1, _pool_max(), dsn=url)
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
    search_path: str | None = None,
) -> tuple[list[str], list[list[Any]]]:
    # None, not {}: psycopg2 attempts %-interpolation whenever vars is not None, so an
    # unparameterised statement containing a literal % (LIKE '%tax%') would crash.
    binds = binds or None
    with warehouse_connection(organization_id) as conn:
        with conn.cursor() as cur:
            # A hard server-side ceiling as well as the LIMIT the builder writes: a
            # governed portal must not be able to hold a client warehouse open on one
            # badly-shaped request.
            cur.execute("SET LOCAL statement_timeout = '30s'")
            if search_path:
                # Scopes UNQUALIFIED names for callers like the SQL workspace. SET LOCAL
                # dies with the rolled-back transaction, so it never leaks to the next
                # borrower. A comma-separated value ('cisadm, reporting') must be passed
                # as SEPARATE parameters — a single %s binds one quoted name and
                # 'cisadm, reporting' resolves to nothing.
                schemas = [s.strip() for s in search_path.split(",") if s.strip()]
                placeholders = ", ".join(["%s"] * len(schemas))
                cur.execute(f"SET LOCAL search_path = {placeholders}", schemas)
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
