"""When this organization's reporting tables were last built, and whether that is too long ago.

Builds run every six hours with a daily full refresh, so more than a day and a half since the
last one means at least a day of missed refreshes (Ellensburg 2026-09-29: 19 days, a stranded
swap table blocking every build, and no page said so). GET /portal/freshness answers for the
caller's organization; the app shell warns on every page when it is stale.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from api.auth.dependencies import AuthContext, require_permission
from api.data_version import data_version
from api.org_db import require_org_for_data
from api.snapshot_catalog import org_backend
from api.warehouse_db import warehouse_connection

STALE_HOURS = 36
RECHECK_SECONDS = 60

router = APIRouter(prefix="/portal", tags=["freshness"])


def refresh_marker(org: str, engine: str) -> str:
    """A value that changes when the warehouse is rebuilt. Oracle in-database: the build stamp
    (staging synthesizes load_dttm, CISADM carries none). Postgres: load_dttm, the CDC/build
    watermark as of the last build (the reporting table's "Load Date/Time")."""
    if engine == "oracle":
        return data_version(org) or "none"
    with warehouse_connection(org) as conn:
        cur = conn.cursor()
        try:
            # the built reporting table, not the staging VIEW: CDC keeps landing (and a view's
            # max current) while a failed dbt build leaves the reporting tables behind
            cur.execute('select max("Load Date/Time")::text from reporting.rpt_financial_txn')
            row = cur.fetchone()
            return str(row[0]) if row and row[0] else "none"
        except Exception:  # noqa: BLE001
            return "none"


def built_at(marker: str, engine: str) -> str | None:
    """The build time as ISO. Oracle: the stamp's LAST_DDL half with the server clock's offset
    (last_analyzed:last_ddl:count[:offset]); statistics can be regathered without a rebuild,
    the tables' creation cannot."""
    if marker == "none":
        return None
    if engine == "oracle":
        parts = marker.split(":")
        if len(parts) not in (3, 4) or len(parts[1]) != 14:
            return None
        d = parts[1]
        offset = f"{parts[3][:3]}:{parts[3][3:]}" if len(parts) == 4 and len(parts[3]) == 5 else ""
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}T{d[8:10]}:{d[10:12]}:{d[12:]}{offset}"
    return marker.replace(" ", "T", 1)


_memo: dict[str, tuple[float, str | None]] = {}
_lock = threading.Lock()


def clear() -> None:
    with _lock:
        _memo.clear()


def _last_build(org: str) -> str | None:
    """Read at most once a minute per organization: every page asks."""
    with _lock:
        hit = _memo.get(org)
    if hit and time.monotonic() - hit[0] < RECHECK_SECONDS:
        return hit[1]
    engine, _ = org_backend(org)
    when = built_at(refresh_marker(org, engine), engine)
    with _lock:
        _memo[org] = (time.monotonic(), when)
    return when


def freshness(org: str, *, now: datetime | None = None) -> dict[str, Any]:
    when = _last_build(org)
    if not when:
        return {"built_at": None, "age_hours": None, "stale": False}
    built = datetime.fromisoformat(when)
    built = built if built.tzinfo else built.astimezone()   # no offset: the API host's clock
    age = ((now or datetime.now(timezone.utc)) - built).total_seconds() / 3600
    return {"built_at": when, "age_hours": round(age, 1), "stale": age > STALE_HOURS}


@router.get("/freshness")
def freshness_route(ctx: AuthContext = Depends(require_permission("portal:read"))) -> dict[str, Any]:
    return freshness(require_org_for_data(ctx))
