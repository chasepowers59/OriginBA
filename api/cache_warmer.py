"""After a warehouse rebuild, build the home and workstream summaries once in the background,
so the first reader each morning is not the one who waits.

Every minute, for each organization with a warehouse: when its build stamp
(api/data_version.py) is new, build what those pages ask for by default -- 30 days, no
comparison, no filters -- for a reader with every workstream and no row rules, through the
routes' own cache functions; and on each canvas of a million rows or more, the report the
explorer runs when the page opens (its first ready-to-run report over the canvas's default
window, api/date_presets.py), which is the ~25 s wait at Ellensburg volume. An unknown stamp does nothing; a failed build is logged and the
rest carry on. Off under tests and with PORTAL_WARM_CACHE=false. One per API process, since
each process keeps its own cache.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import date, datetime, timezone
from typing import Any

from api.data_version import data_version
from api.date_presets import preset_range
from api.reporting_dates import data_as_of

log = logging.getLogger("originba.api")
INTERVAL_SECONDS = 60
WARM_MIN_ROWS = 1_000_000
_warmed: dict[str, str] = {}
_last: dict[str, dict[str, Any]] = {}
_started = threading.Event()


def enabled() -> bool:
    return os.environ.get("ENVIRONMENT") != "test" and os.environ.get("PORTAL_WARM_CACHE", "").lower() != "false"


def _workstreams(org_id: str) -> list[str]:
    from api.snapshot_catalog import list_workstreams
    from api.workstream_dashboard import WORKSTREAM_KPIS
    return [w["id"] for w in list_workstreams(org_id) if w.get("id") in WORKSTREAM_KPIS]


def _opening_reports(org_id: str) -> list[tuple[str, Any]]:
    """Each large canvas's opening report, as the explorer sends it (ExplorerPanel.runPremade):
    the default window on the canvas's date field, then the report's own filters."""
    from api import snapshot_explorer as se
    from api.snapshot_catalog import load_catalog

    catalog = load_catalog(organization_id=org_id)
    enabled = set(catalog.get("portal_snapshots") or catalog["snapshots"])
    anchored = data_as_of(org_id)
    end = date.fromisoformat(anchored) if anchored else date.today()
    jobs = []
    for snapshot_id, snapshot in catalog["snapshots"].items():
        reports = snapshot.get("premade_reports") or []
        if snapshot_id not in enabled or not reports or (se._row_estimate(snapshot, org_id) or 0) < WARM_MIN_ROWS:
            continue
        field = snapshot.get("default_date_field") or ((snapshot.get("date_fields") or [{}])[0] or {}).get("id")
        window = [{"field": field, "op": "between", "value": preset_range(snapshot.get("default_date_preset"), end)}] if field else []
        body = se.QueryRequest(dimensions=reports[0]["dimensions"], measures=reports[0]["measures"],
                               filters=window + list(reports[0].get("filters") or []), time_dimensions=[], limit=500)
        jobs.append((f"report {snapshot_id}", lambda s=snapshot, b=body: se.cached_query(
            org_id, s, b, [f.model_dump() for f in b.filters])))
    return jobs


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
    try:
        jobs += _opening_reports(org_id)
    except Exception as exc:  # noqa: BLE001 -- the summaries are still worth building
        log.warning("cache warm %s reports skipped: %s", org_id, exc)
    built, failed = [], []
    for name, job in jobs:
        try:
            job()
            built.append(name)
        except Exception as exc:  # noqa: BLE001 -- one page failing must not stop the others
            failed.append(name)
            log.warning("cache warm %s %s failed: %s", org_id, name, exc)
    _last[org_id] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "version": version,
                     "built": built, "failed": failed}
    return built


def status() -> dict[str, dict[str, Any]]:
    """Each organization's last warm, for System health."""
    return {org: dict(v) for org, v in _last.items()}


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
    _last.clear()
