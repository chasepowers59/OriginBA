"""After a warehouse rebuild, build the home and workstream summaries once in the background,
so the first reader each morning is not the one who waits.

Every minute, for each organization with a warehouse: when its build stamp
(api/data_version.py) is new, build what those pages ask for by default -- 30 days, no
comparison, no filters -- for a reader with every workstream and no row rules, through the
routes' own cache functions. An unknown stamp does nothing; a failed build is logged and the
rest carry on. Off under tests and with PORTAL_WARM_CACHE=false. One per API process, since
each process keeps its own cache.
"""
from __future__ import annotations

import logging
import os
import threading

from api.data_version import data_version

log = logging.getLogger("originba.api")
INTERVAL_SECONDS = 60
_warmed: dict[str, str] = {}
_started = threading.Event()


def enabled() -> bool:
    return os.environ.get("ENVIRONMENT") != "test" and os.environ.get("PORTAL_WARM_CACHE", "").lower() != "false"


def _workstreams(org_id: str) -> list[str]:
    from api.snapshot_catalog import list_workstreams
    from api.workstream_dashboard import WORKSTREAM_KPIS
    return [w["id"] for w in list_workstreams(org_id) if w.get("id") in WORKSTREAM_KPIS]


def warm_once(org_id: str) -> list[str]:
    """What was built for this organization: nothing unless its stamp is new."""
    from api.snapshot_explorer import cached_home_summary, cached_workstream_summary

    version = data_version(org_id)
    if not version or _warmed.get(org_id) == version:
        return []
    _warmed[org_id] = version
    jobs = [("home", lambda: cached_home_summary(org_id, 30, False, "prior_period", [], ["*"], {}, ()))]
    jobs += [(ws, lambda ws=ws: cached_workstream_summary(org_id, ws, 30, False, "prior_period", [], ()))
             for ws in _workstreams(org_id)]
    built = []
    for name, job in jobs:
        try:
            job()
            built.append(name)
        except Exception as exc:  # noqa: BLE001 -- one page failing must not stop the others
            log.warning("cache warm %s %s failed: %s", org_id, name, exc)
    return built


def _organizations() -> list[str]:
    from api.demo_db import demo_configured
    from api.organizations import load_organizations
    from api.warehouse_db import warehouse_configured
    return [str(o["id"]) for o in load_organizations() if demo_configured(str(o["id"])) or warehouse_configured(str(o["id"]))]


def _loop(stop: threading.Event) -> None:
    while not stop.wait(INTERVAL_SECONDS):
        for org_id in _organizations():
            built = warm_once(org_id)
            if built:
                log.info("cache warmed org=%s pages=%s", org_id, ",".join(built))


def start(stop: threading.Event) -> None:
    if enabled() and not _started.is_set():
        _started.set()
        threading.Thread(target=_loop, args=(stop,), name="cache-warmer", daemon=True).start()


def reset() -> None:
    _warmed.clear()
