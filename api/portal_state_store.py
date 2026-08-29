"""Shared Postgres store for portal user-state (saved views, dashboards, DQ acks).

WHY: the JSON file stores work for a single local process but not for a deployed
portal running as MANY stateless replicas -- each would see a different file and
lose writes. When a Postgres URL is configured this backs those collections with
one shared table (portal_state.records); otherwise it stays disabled and the
callers keep their local JSON files, so local dev needs no database.

DSN resolution (first that is Postgres wins): PORTAL_STATE_DATABASE_URL, then
PORTAL_AUTH_DATABASE_URL (the same Supabase database the auth tables live in).
"""
from __future__ import annotations

import os
import threading
from typing import Any

_pool = None
_pool_lock = threading.Lock()
_resolved_dsn: str | None = None


def _dsn() -> str | None:
    for key in ("PORTAL_STATE_DATABASE_URL", "PORTAL_AUTH_DATABASE_URL"):
        url = (os.getenv(key) or "").strip()
        if url.startswith("postgres://") or url.startswith("postgresql://"):
            return url
    return None


def enabled() -> bool:
    return _dsn() is not None


def _get_pool():
    global _pool, _resolved_dsn
    dsn = _dsn()
    if dsn is None:
        return None
    with _pool_lock:
        if _pool is None or _resolved_dsn != dsn:
            from psycopg2.pool import ThreadedConnectionPool

            # Supabase requires TLS; add it if the caller's URL omits it.
            if "sslmode=" not in dsn:
                dsn = dsn + ("&" if "?" in dsn else "?") + "sslmode=require"
            _pool = ThreadedConnectionPool(1, 8, dsn=dsn)
            _resolved_dsn = _dsn()
    return _pool


class _conn:
    """Borrow/return a pooled connection, rolling back on the way out."""

    def __enter__(self):
        self._pool = _get_pool()
        self._c = self._pool.getconn()
        return self._c

    def __exit__(self, *exc):
        try:
            self._c.rollback()
        except Exception:  # noqa: BLE001
            pass
        self._pool.putconn(self._c)


def list_records(collection: str, organization_id: str) -> list[dict[str, Any]]:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "select data from portal_state.records "
            "where collection = %s and organization_id = %s "
            "order by updated_at desc",
            (collection, organization_id),
        )
        return [row[0] for row in cur.fetchall()]


def upsert(collection: str, record_id: str, organization_id: str, data: dict[str, Any]) -> None:
    import json

    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "insert into portal_state.records (collection, id, organization_id, data, updated_at) "
            "values (%s, %s, %s, %s::jsonb, now()) "
            "on conflict (collection, id) do update set "
            "data = excluded.data, organization_id = excluded.organization_id, updated_at = now()",
            (collection, record_id, organization_id, json.dumps(data)),
        )
        c.commit()


def delete(collection: str, record_id: str, organization_id: str) -> bool:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "delete from portal_state.records "
            "where collection = %s and id = %s and organization_id = %s",
            (collection, record_id, organization_id),
        )
        deleted = cur.rowcount > 0
        c.commit()
        return deleted


def count(collection: str, organization_id: str) -> int:
    with _conn() as c, c.cursor() as cur:
        cur.execute(
            "select count(*) from portal_state.records "
            "where collection = %s and organization_id = %s",
            (collection, organization_id),
        )
        return int(cur.fetchone()[0])
