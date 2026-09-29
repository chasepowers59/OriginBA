"""The warehouse's build stamp per organization: it changes whenever dbt rebuilds or merges
into a reporting canvas, so a result keyed by it can be kept until the data changes
(api/summary_cache.py) instead of for five minutes.

Postgres: each reporting table's identity (a dbt table rebuild is a new table) plus its
insert/update/delete counters (an incremental merge, rpt_billed_charge, keeps the table).
Oracle: the reporting tables' last-analyzed and last-DDL times; every model build gathers
statistics in its post-hook, merges included. Read at most once a minute per organization;
None when it cannot be read, and callers then keep results for five minutes as before.
"""
from __future__ import annotations

import threading
import time

from api.snapshot_catalog import org_backend

RECHECK_SECONDS = 60

_PG = """
select md5(string_agg(c.oid::text || ':' || c.relfilenode::text || ':'
                      || coalesce(s.n_tup_ins + s.n_tup_upd + s.n_tup_del, 0)::text, ',' order by c.oid))
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
left join pg_stat_user_tables s on s.relid = c.oid
where n.nspname = %(schema)s and c.relkind = 'r'
"""

_ORACLE = """
select to_char(max(t.last_analyzed), 'YYYYMMDDHH24MISS') || ':'
       || to_char(max(o.last_ddl_time), 'YYYYMMDDHH24MISS') || ':' || count(*)
from all_tables t
join all_objects o on o.owner = t.owner and o.object_name = t.table_name and o.object_type = 'TABLE'
where t.owner = :owner
"""

_memo: dict[str, tuple[float, str | None]] = {}
_lock = threading.Lock()


def _read(organization_id: str) -> str | None:
    engine, _ = org_backend(organization_id)
    if engine == "oracle":
        from api.demo_db import execute_query
        _, rows = execute_query(_ORACLE, {"owner": "ORIGINBA_REPORTING"}, organization_id=organization_id, max_rows=1)
    else:
        from api.warehouse_db import execute_query
        _, rows = execute_query(_PG, {"schema": "reporting"}, organization_id=organization_id, max_rows=1)
    return str(rows[0][0]) if rows and rows[0][0] is not None else None


def data_version(organization_id: str) -> str | None:
    with _lock:
        hit = _memo.get(organization_id)
    if hit and time.monotonic() - hit[0] < RECHECK_SECONDS:
        return hit[1]
    try:
        version = _read(organization_id)
    except Exception:  # noqa: BLE001 -- a stamp is an optimisation, never a reason to fail a page
        version = None
    with _lock:
        _memo[organization_id] = (time.monotonic(), version)
    return version


def known() -> dict[str, dict]:
    """Each organization's last read stamp and how many seconds ago it was read."""
    now = time.monotonic()
    with _lock:
        return {org: {"version": v, "read_seconds_ago": int(now - at)} for org, (at, v) in _memo.items()}


def clear() -> None:
    with _lock:
        _memo.clear()
