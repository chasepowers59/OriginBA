"""Scheduled report delivery — a saved view, on a cadence, in the inbox.

A schedule subscribes recipients to a SAVED VIEW (the governed builder artifact —
never raw SQL) with a trailing data window. The runner (report_schedule_runner.py,
invoked by cron / a Render cron job) renders each due schedule through the same
query builder the portal uses and mails the result as a CSV attachment via
env-configured SMTP:

    SMTP_HOST / SMTP_PORT (587) / SMTP_USERNAME / SMTP_PASSWORD /
    SMTP_FROM / SMTP_STARTTLS (default true)

Storage follows saved_views.py exactly: portal_state.records when the shared
Postgres is configured, a local JSON file otherwise — so local dev needs nothing.
"""
from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from api import portal_state_store as _pss
from api.saved_views import list_saved_views

ROOT = Path(__file__).resolve().parent.parent
SCHEDULES_PATH = ROOT / "data" / "analytics_portal" / "report_schedules.json"
_COLLECTION = "report_schedules"
MAX_SCHEDULES = 20
CADENCES = ("daily", "weekly", "monthly")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ScheduleError(ValueError):
    pass


# --- store (portal_state when configured, local JSON otherwise) --------------------

def _load_store() -> dict[str, Any]:
    if SCHEDULES_PATH.exists():
        return json.loads(SCHEDULES_PATH.read_text(encoding="utf-8"))
    return {"schedules": []}


def _save_store(data: dict[str, Any]) -> None:
    SCHEDULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _find_view(view_id: str, organization_id: str) -> dict[str, Any] | None:
    for view in list_saved_views(organization_id):
        if view.get("id") == view_id:
            return view
    return None


def list_schedules(organization_id: str) -> list[dict[str, Any]]:
    if _pss.enabled():
        return _pss.list_records(_COLLECTION, organization_id)
    return [s for s in _load_store().get("schedules", [])
            if s.get("organization_id") == organization_id]


def _all_schedules() -> list[dict[str, Any]]:
    """Every org's schedules — the runner sweeps all of them."""
    if _pss.enabled():
        return _pss.list_all_records(_COLLECTION)
    return list(_load_store().get("schedules", []))


def create_schedule(payload: dict[str, Any], *, organization_id: str,
                    created_by: str) -> dict[str, Any]:
    view_id = str(payload.get("saved_view_id") or "")
    view = _find_view(view_id, organization_id)
    if view is None:
        raise ScheduleError("Unknown saved view for this organization")

    recipients = [str(r).strip().lower() for r in (payload.get("recipients") or [])]
    if not recipients:
        raise ScheduleError("At least one recipient is required")
    for r in recipients:
        if not _EMAIL_RE.match(r):
            raise ScheduleError(f"Not a valid email address: {r}")

    cadence = str(payload.get("cadence") or "daily")
    if cadence not in CADENCES:
        raise ScheduleError(f"Cadence must be one of {', '.join(CADENCES)}")
    weekday = int(payload.get("weekday") or 0)
    if cadence == "weekly" and not 0 <= weekday <= 6:
        raise ScheduleError("Weekday must be 0 (Monday) through 6 (Sunday)")
    hour_utc = int(payload.get("hour_utc") or 13)
    if not 0 <= hour_utc <= 23:
        raise ScheduleError("hour_utc must be 0-23")
    window_days = int(payload.get("window_days") or 30)
    if not 1 <= window_days <= 366:
        raise ScheduleError("window_days must be 1-366")

    if len(list_schedules(organization_id)) >= MAX_SCHEDULES:
        raise ScheduleError(f"Schedule limit reached ({MAX_SCHEDULES} per organization)")

    entry = {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "saved_view_id": view_id,
        "view_title": view.get("title"),
        "snapshot_id": view.get("snapshot_id"),
        "recipients": recipients,
        "cadence": cadence,
        "weekday": weekday,
        "hour_utc": hour_utc,
        "window_days": window_days,
        "format": "csv",
        "enabled": True,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run_at": None,
        "last_status": None,
    }
    if _pss.enabled():
        _pss.upsert(_COLLECTION, entry["id"], organization_id, entry)
    else:
        store = _load_store()
        store.setdefault("schedules", []).append(entry)
        _save_store(store)
    return entry


def delete_schedule(schedule_id: str, organization_id: str) -> bool:
    if _pss.enabled():
        return _pss.delete(_COLLECTION, schedule_id, organization_id)
    store = _load_store()
    before = len(store.get("schedules", []))
    store["schedules"] = [
        s for s in store.get("schedules", [])
        if not (s.get("id") == schedule_id and s.get("organization_id") == organization_id)]
    if len(store["schedules"]) == before:
        return False
    _save_store(store)
    return True


def _update_schedule(entry: dict[str, Any]) -> None:
    if _pss.enabled():
        _pss.upsert(_COLLECTION, entry["id"], entry["organization_id"], entry)
        return
    store = _load_store()
    store["schedules"] = [
        entry if s.get("id") == entry["id"] else s for s in store.get("schedules", [])]
    _save_store(store)


# --- calendar logic (pure) ---------------------------------------------------------

def is_due(schedule: dict[str, Any], now: datetime) -> bool:
    """Due once per period, at/after the configured UTC hour."""
    if not schedule.get("enabled", True):
        return False
    if now.hour < int(schedule.get("hour_utc") or 13):
        return False
    cadence = schedule.get("cadence", "daily")
    if cadence == "weekly" and now.weekday() != int(schedule.get("weekday") or 0):
        return False
    if cadence == "monthly" and now.day != 1:
        return False
    last = schedule.get("last_run_at")
    if last:
        last_dt = datetime.fromisoformat(last)
        if last_dt.date() == now.date():
            return False  # already ran this period (all cadences fire at most daily)
    return True


# --- rendering ---------------------------------------------------------------------

def render_schedule(schedule: dict[str, Any], view: dict[str, Any]):
    """Run the saved view through the SAME governed query path the portal uses.

    Returns (columns, labels, rows). The date filter is a trailing window ending
    now — a schedule that mails a frozen date range weekly would go stale.
    """
    from api.query_builder import build_query
    from api.snapshot_catalog import allowed_fields, get_snapshot, snapshot_backend

    org_id = schedule["organization_id"]
    snapshot = get_snapshot(view["snapshot_id"], org_id)
    backend, dialect, schema = snapshot_backend(snapshot, org_id)

    filters: list[dict[str, Any]] = []
    date_field = snapshot.get("required_date_field")
    if date_field:
        end = datetime.now(timezone.utc).date()
        start = end - timedelta(days=int(schedule.get("window_days") or 30))
        filters.append({"field": date_field, "op": "between",
                        "value": [start.isoformat(), end.isoformat()]})
    if view.get("scope_field") and view.get("scope_value") is not None:
        filters.append({"field": view["scope_field"], "op": "eq",
                        "value": view["scope_value"]})

    measures = view.get("measures") or [{
        "field": view.get("measure_field") or "*",
        "agg": view.get("measure_agg") or "count"}]
    trusted = set(snapshot.get("trusted_measures", []))
    sql, binds = build_query(
        table_name=snapshot["table_name"],
        allowed_fields=allowed_fields(snapshot),
        trusted_measures=trusted if dialect != "oracle" else {m.upper() for m in trusted},
        required_date_field=date_field,
        dimensions=view.get("dimensions") or [],
        measures=measures,
        filters=filters,
        limit=snapshot.get("max_rows", 500),
        time_dimensions=[],
        dialect=dialect,
        schema=schema,
    )
    if backend == "postgres":
        from api.warehouse_db import execute_query as run
    else:
        from api.demo_db import execute_query as run
    columns, raw_rows = run(sql, binds, organization_id=org_id, max_rows=500)

    from api.snapshot_explorer import _result_labels, _serialize_value
    labels = _result_labels(snapshot, columns, view.get("dimensions") or [], measures, [])
    rows = [{columns[i]: _serialize_value(r[i]) for i in range(len(columns))}
            for r in raw_rows]
    return columns, labels, rows


def rows_to_csv(columns: list[str], labels: dict[str, str],
                rows: list[dict[str, Any]]) -> str:
    """CSV with business labels as the header; booleans render True/False, None empty
    — the same conventions as the SPA's exports."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([labels.get(c, c) for c in columns])
    for row in rows:
        out = []
        for c in columns:
            v = row.get(c)
            if v is None:
                out.append("")
            elif isinstance(v, bool):
                out.append("True" if v else "False")
            else:
                out.append(v)
        writer.writerow(out)
    return buf.getvalue()


# --- delivery ----------------------------------------------------------------------

def smtp_configured() -> bool:
    import os
    return bool((os.environ.get("SMTP_HOST") or "").strip())


def _build_message(schedule: dict[str, Any], csv_text: str, now: datetime):
    from email.message import EmailMessage
    import os

    msg = EmailMessage()
    title = schedule.get("view_title") or schedule.get("snapshot_id") or "Report"
    msg["Subject"] = f"{title} — {now.date().isoformat()}"
    msg["From"] = (os.environ.get("SMTP_FROM") or "reports@originba.local").strip()
    msg["To"] = ", ".join(schedule.get("recipients", []))
    msg.set_content(
        f"Scheduled report: {title}\n"
        f"Data window: trailing {schedule.get('window_days', 30)} days as of {now.date()}.\n\n"
        "The data is attached as CSV. Open the portal for the interactive view.\n")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(title))[:60] or "report"
    msg.add_attachment(csv_text.encode("utf-8"), maintype="text", subtype="csv",
                       filename=f"{safe}_{now.date().isoformat()}.csv")
    return msg


def _smtp_send(msg) -> None:
    import os
    import smtplib

    host = (os.environ.get("SMTP_HOST") or "").strip()
    if not host:
        raise ScheduleError("SMTP_HOST is not configured")
    port = int(os.environ.get("SMTP_PORT") or 587)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if (os.environ.get("SMTP_STARTTLS") or "true").lower() != "false":
            smtp.starttls()
        user = (os.environ.get("SMTP_USERNAME") or "").strip()
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD") or "")
        smtp.send_message(msg)


def run_due_schedules(*, now: datetime | None = None,
                      send: Callable[[Any], None] | None = None,
                      dry_run: bool = False) -> list[dict[str, Any]]:
    """Render + deliver every due schedule. One failure never blocks the rest;
    dry-run renders but neither sends nor marks the schedule as run."""
    now = now or datetime.now(timezone.utc)
    send = send or _smtp_send
    results: list[dict[str, Any]] = []
    for schedule in _all_schedules():
        if not is_due(schedule, now):
            continue
        result = {"id": schedule["id"], "view": schedule.get("view_title"),
                  "recipients": schedule.get("recipients", [])}
        try:
            view = _find_view(schedule["saved_view_id"], schedule["organization_id"])
            if view is None:
                raise ScheduleError("Saved view no longer exists")
            columns, labels, rows = render_schedule(schedule, view)
            csv_text = rows_to_csv(columns, labels, rows)
            result["row_count"] = len(rows)
            if dry_run:
                result["status"] = "dry-run"
            else:
                send(_build_message(schedule, csv_text, now))
                result["status"] = "sent"
                schedule["last_run_at"] = now.isoformat()
                schedule["last_status"] = f"sent {len(rows)} rows"
                _update_schedule(schedule)
        except Exception as exc:  # noqa: BLE001 — the runner must survive any one failure
            result["status"] = f"error: {exc}"
            schedule["last_status"] = f"error: {exc}"
            _update_schedule(schedule)
        results.append(result)
    return results
