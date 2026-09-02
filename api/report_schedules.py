"""Scheduled report delivery — a saved view, on a cadence, in the inbox.

A schedule subscribes recipients to a SAVED VIEW (the governed builder artifact —
never raw SQL) with a trailing data window. The runner (report_schedule_runner.py,
invoked hourly by cron) renders each due schedule through the same query builder
the portal uses and mails the result as a CSV attachment.
"""
from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from api.notifications import build_message, clean_recipients, send_message
from api.org_store import OrgRecordStore
from api.reporting_dates import window_date_field
from api.saved_views import list_saved_views

ROOT = Path(__file__).resolve().parent.parent
SCHEDULES_PATH = ROOT / "data" / "analytics_portal" / "report_schedules.json"
MAX_SCHEDULES = 20
CADENCES = ("daily", "weekly", "monthly")

_store = OrgRecordStore("report_schedules", lambda: SCHEDULES_PATH, "schedules")


class ScheduleError(ValueError):
    pass


def _find_view(view_id: str, organization_id: str) -> dict[str, Any] | None:
    for view in list_saved_views(organization_id):
        if view.get("id") == view_id:
            return view
    return None


def list_schedules(organization_id: str) -> list[dict[str, Any]]:
    return _store.list(organization_id)


def create_schedule(payload: dict[str, Any], *, organization_id: str,
                    created_by: str) -> dict[str, Any]:
    view_id = str(payload.get("saved_view_id") or "")
    view = _find_view(view_id, organization_id)
    if view is None:
        raise ScheduleError("Unknown saved view for this organization")

    try:
        recipients = clean_recipients(payload.get("recipients"))
    except ValueError as exc:
        raise ScheduleError(str(exc)) from exc

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

    return _store.add({
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
        "enabled": True,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run_at": None,
        "last_status": None,
    })


def delete_schedule(schedule_id: str, organization_id: str) -> bool:
    return _store.delete(schedule_id, organization_id)


def is_due(schedule: dict[str, Any], now: datetime) -> bool:
    """Due once per period, at or after the configured UTC hour."""
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
    # All cadences fire at most once a day, so a same-day run means done.
    return not (last and datetime.fromisoformat(last).date() == now.date())


def render_schedule(schedule: dict[str, Any], view: dict[str, Any]):
    """Run the saved view through the SAME governed query path the portal uses.

    Returns (columns, labels, rows). The date filter is a trailing window ending
    now — a schedule that mailed a frozen date range weekly would go stale.
    """
    from api.query_builder import build_query
    from api.reporting_dates import reporting_window
    from api.snapshot_catalog import allowed_fields, get_snapshot, snapshot_backend
    from api.snapshot_explorer import _result_labels, _serialize_value

    org_id = schedule["organization_id"]
    snapshot = get_snapshot(view["snapshot_id"], org_id)
    backend, dialect, schema = snapshot_backend(snapshot, org_id)

    filters: list[dict[str, Any]] = []
    date_field = schedule_date_field(snapshot)
    window_days = int(schedule.get("window_days") or 30)
    # reporting_today(), not a UTC date: this window filters BUSINESS dates, and every
    # other window builder (kpi_runner, nlq_metrics, snapshot_explorer) ends on the
    # local calendar date. On a non-UTC server the two disagreed for the offset's worth
    # of hours each day -- six here -- so a scheduled report's "last 30 days" ended a
    # day later than the same window on screen and the emailed figure did not tie.
    start_iso, end_iso = reporting_window(window_days)
    if date_field:
        filters.append({"field": date_field, "op": "between",
                        "value": [start_iso, end_iso]})
    # The email quotes THIS, written where the filter is decided, so the two cannot drift.
    schedule["window_note"] = window_sentence(date_field, window_days, end_iso)
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

    labels = _result_labels(snapshot, columns, view.get("dimensions") or [], measures, [])
    rows = [{columns[i]: _serialize_value(r[i]) for i in range(len(columns))}
            for r in raw_rows]
    return columns, labels, rows


def rows_to_csv(columns: list[str], labels: dict[str, str],
                rows: list[dict[str, Any]]) -> str:
    """Business labels as the header; booleans True/False, None empty — the same
    conventions as the SPA's exports."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow([labels.get(c, c) for c in columns])
    for row in rows:
        out: list[Any] = []
        for c in columns:
            v = row.get(c)
            out.append("" if v is None else "True" if v is True else "False" if v is False else v)
        writer.writerow(out)
    return buf.getvalue()


# The rule this module discovered has four callers now -- schedules, the KPI runner, NLQ
# metrics, and the explorer's default window -- so it lives in reporting_dates beside the
# window arithmetic. Kept under the name this module's callers already import.
schedule_date_field = window_date_field


def window_sentence(date_field: str | None, window_days: int, as_of: str) -> str:
    """Describe the window that was ACTUALLY applied.

    Names the field as well as the span: "trailing 30 days" is ambiguous on a canvas
    carrying eight date columns, and a reader who cannot tell which one was windowed
    cannot check the number.
    """
    if not date_field:
        return "Data window: all rows — this canvas carries no date to window on."
    return f"Data window: trailing {window_days} days on {date_field}, as of {as_of}."


def _message(schedule: dict[str, Any], csv_text: str, now: datetime):
    title = schedule.get("view_title") or schedule.get("snapshot_id") or "Report"
    msg = build_message(
        f"{title} — {now.date().isoformat()}",
        schedule.get("recipients", []),
        f"Scheduled report: {title}\n"
        f"{schedule.get('window_note') or ''}\n\n"
        "The data is attached as CSV. Open the portal for the interactive view.\n")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(title))[:60] or "report"
    msg.add_attachment(csv_text.encode("utf-8"), maintype="text", subtype="csv",
                       filename=f"{safe}_{now.date().isoformat()}.csv")
    return msg


def deliver(schedule: dict[str, Any], view: dict[str, Any], now: datetime,
            send: Callable[[Any], None]) -> int:
    """Render and send one schedule; returns the row count delivered."""
    columns, labels, rows = render_schedule(schedule, view)
    send(_message(schedule, rows_to_csv(columns, labels, rows), now))
    return len(rows)


def run_due_schedules(*, now: datetime | None = None,
                      send: Callable[[Any], None] | None = None,
                      dry_run: bool = False) -> list[dict[str, Any]]:
    """Deliver every due schedule. One failure never blocks the rest; dry-run
    renders but neither sends nor marks the schedule as run."""
    now = now or datetime.now(timezone.utc)
    send = send or send_message
    results: list[dict[str, Any]] = []
    for schedule in _store.list_all():
        if not is_due(schedule, now):
            continue
        result = {"id": schedule["id"], "view": schedule.get("view_title"),
                  "recipients": schedule.get("recipients", [])}
        try:
            view = _find_view(schedule["saved_view_id"], schedule["organization_id"])
            if view is None:
                raise ScheduleError("Saved view no longer exists")
            if dry_run:
                columns, labels, rows = render_schedule(schedule, view)
                result.update(status="dry-run", row_count=len(rows))
            else:
                count = deliver(schedule, view, now, send)
                result.update(status="sent", row_count=count)
                schedule["last_run_at"] = now.isoformat()
                schedule["last_status"] = f"sent {count} rows"
                _store.update(schedule)
        except Exception as exc:  # noqa: BLE001 — the runner must survive any one failure
            result["status"] = f"error: {exc}"
            schedule["last_status"] = f"error: {exc}"
            _store.update(schedule)
        results.append(result)
    return results
