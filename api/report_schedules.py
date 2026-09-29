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
from xml.sax.saxutils import escape as xml_escape
import uuid
from datetime import datetime, timedelta, timezone
from numbers import Number
from pathlib import Path
from typing import Any, Callable

from api.notifications import build_message, clean_recipients, send_message
from api.org_store import OrgRecordStore
from api.portal_config import pdf_logo_path
from api.row_security import creator_rules, row_filters
from api.reporting_dates import window_date_field
from api.saved_views import list_saved_views

ROOT = Path(__file__).resolve().parent.parent
SCHEDULES_PATH = ROOT / "data" / "analytics_portal" / "report_schedules.json"
MAX_SCHEDULES = 20
CADENCES = ("daily", "weekly", "monthly")
FORMATS = ("csv", "xlsx", "pdf")

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
                    created_by: str, row_rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    fmt = str(payload.get("format") or "csv").lower()
    if fmt not in FORMATS:
        raise ScheduleError(f"Format must be one of {', '.join(FORMATS)}")
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
    # `or 13` would turn a deliberate 0 (midnight UTC) into 13:00; only ABSENCE defaults.
    hour_utc = 13 if payload.get("hour_utc") is None else int(payload["hour_utc"])
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
        "format": fmt,
        "enabled": True,
        "created_by": created_by,
        # The creator's row-level security, kept: the run at 06:00 has nobody signed in.
        "row_rules": list(row_rules or []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_run_at": None,
        "last_status": None,
    })


def delete_schedule(schedule_id: str, organization_id: str) -> bool:
    return _store.delete(schedule_id, organization_id)


def _last_occurrence(schedule: dict[str, Any], now: datetime) -> datetime:
    """The most recent scheduled moment at or before `now`."""
    hour = schedule.get("hour_utc")
    at = now.replace(hour=13 if hour is None else int(hour), minute=0, second=0, microsecond=0)
    cadence = schedule.get("cadence", "daily")
    if cadence == "weekly":
        at -= timedelta(days=(now.weekday() - int(schedule.get("weekday") or 0)) % 7)
        return at if at <= now else at - timedelta(days=7)
    if cadence == "monthly":
        at = at.replace(day=1)
        if at > now:
            at = (at - timedelta(days=1)).replace(day=1)
        return at
    return at if at <= now else at - timedelta(days=1)


def is_due(schedule: dict[str, Any], now: datetime) -> bool:
    """Due when a scheduled moment has passed that this schedule has not run for.

    A missed moment is caught up once: the runner fired a monthly report only if it
    happened to run on the 1st, so one down hour lost the month. A schedule with no run
    and no creation time fires only on its scheduled day, never retroactively.
    """
    if not schedule.get("enabled", True):
        return False
    due = _last_occurrence(schedule, now)
    since = schedule.get("last_run_at") or schedule.get("created_at")
    if not since:
        return due.date() == now.date()
    return due > datetime.fromisoformat(since)


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
    start_iso, end_iso = reporting_window(window_days, organization_id=org_id)
    if date_field:
        filters.append({"field": date_field, "op": "between",
                        "value": [start_iso, end_iso]})
    # The email quotes THIS, written where the filter is decided, so the two cannot drift.
    schedule["window_note"] = window_sentence(date_field, window_days, end_iso)
    if view.get("scope_field") and view.get("scope_value") is not None:
        filters.append({"field": view["scope_field"], "op": "eq",
                        "value": view["scope_value"]})
    # The view's own filters, as saved: without them the emailed rows could differ from
    # the view on screen. A saved range on the windowed date gives way to the trailing
    # window above -- a schedule that mailed the same fixed dates every week would go stale.
    filters.extend(f for f in view.get("filters") or []
                   if not (date_field and f.get("field") == date_field))
    # The creator's CURRENT rules (a deactivated creator stops it). Raises RowAccessDenied, recorded
    # as the run's error, if the creator is gone or the canvas lacks a rule's column.
    filters.extend(row_filters(creator_rules(schedule.get("created_by", ""), schedule.get("row_rules")), snapshot))

    measures = view.get("measures") or [{
        "field": view.get("measure_field") or "*",
        "agg": view.get("measure_agg") or "count"}]
    trusted = set(snapshot.get("trusted_measures", []))
    sql, binds = build_query(
        table_name=snapshot["table_name"],
        allowed_fields=allowed_fields(snapshot),
        trusted_measures=trusted,
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


def rows_to_xlsx(columns: list[str], labels: dict[str, str], rows: list[dict[str, Any]]) -> bytes:
    """The same table as rows_to_csv, as a workbook: numbers stay numbers, header bold."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"
    ws.append([labels.get(c, c) for c in columns])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append([None if (v := row.get(c)) is None else "True" if v is True else "False" if v is False
                   else v for c in columns])
        # openpyxl stores a string starting with "=" as a formula; a value is never one
        for cell in ws[ws.max_row]:
            if cell.data_type == "f":
                cell.data_type = "s"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class _Text(str):
    """A text cell (wrapped as a paragraph); numbers and flags stay plain, right-aligned strings."""


def _is_number(v: Any) -> bool:
    # Number, not (int, float): psycopg2 returns NUMERIC money as Decimal, which printed
    # unformatted, left-aligned and without a chart
    return isinstance(v, Number) and not isinstance(v, bool)


def _number_columns(columns: list[str], rows: list[dict[str, Any]]) -> list[str]:
    """The columns holding a number in some row and nothing but numbers (or blanks) in any."""
    return [c for c in columns if any(r.get(c) is not None for r in rows)
            and all(_is_number(r.get(c)) for r in rows if r.get(c) is not None)]


def _pdf_cells(columns: list[str], rows: list[dict[str, Any]]) -> list[list[str]]:
    """Each cell as its display string. A number column with any decimals shows two
    throughout, so 1,234.50 and 99.00 line up instead of 1,234.50 and 99."""
    decimal = {c for c in columns if any(_is_number(v := r.get(c)) and not float(v).is_integer() for r in rows)}

    def cell(c: str, v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, bool):
            return "True" if v else "False"
        if _is_number(v):
            return f"{v:,.2f}" if c in decimal else f"{int(v):,}"
        return _Text(v)
    return [[cell(c, r.get(c)) for c in columns] for r in rows]


_LOGO = Path(__file__).resolve().parent.parent / "apps" / "analytics-portal" / "public" / "origin-logo.png"
_BRAND_BLUE = "#006FAC"


def _bar_chart(columns: list[str], labels: dict[str, str], rows: list[dict[str, Any]], width: float):
    """A horizontal bar chart of the first label column against the first numeric one, top 20,
    or None when the result is not one label against one number."""
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors

    number = next(iter(_number_columns(columns, rows)), None)
    label = next((c for c in columns if c != number and any(isinstance(r.get(c), str) for r in rows)), None)
    if not number or not label:
        return None
    top = [r for r in rows if r.get(number) is not None][:20]
    height = 30 + 16 * len(top)
    d = Drawing(width, height)
    chart = HorizontalBarChart()
    chart.x, chart.y, chart.width, chart.height = 150, 10, width - 170, height - 20
    chart.data = [[float(r[number]) for r in reversed(top)]]
    chart.categoryAxis.categoryNames = [n if len(n := str(r.get(label))) <= 28 else n[:27] + "…"
                                        for r in reversed(top)]
    for axis_labels in (chart.categoryAxis.labels, chart.valueAxis.labels):
        axis_labels.fontName, axis_labels.fontSize = "Helvetica", 7
    # Below 10 the axis ticks at halves: whole counts tick by one, fractions keep a decimal
    # (a count of 3 printed "0 0 1 2 2 2 3").
    small = max(abs(v) for v in chart.data[0]) < 10
    if small and all(v.is_integer() for v in chart.data[0]):
        chart.valueAxis.valueStep = 1
    chart.valueAxis.labelTextFormat = (lambda v: f"{v:,.2f}".rstrip("0").rstrip(".")) if small else (lambda v: f"{v:,.0f}")
    chart.valueAxis.valueMin = min(0, min(chart.data[0]))
    chart.bars[0].fillColor = colors.HexColor(_BRAND_BLUE)
    chart.bars[0].strokeColor = None
    d.add(chart)
    return d


def rows_to_pdf(title: str, window_note: str, columns: list[str], labels: dict[str, str],
                rows: list[dict[str, Any]], now: datetime, chart: bool = False, logo: Path | None = None) -> bytes:
    """A formatted report a schedule can send: the Origin mark and title on every page, the
    window it applied, the table with its header repeated on each page, page numbers."""
    return sections_to_pdf(title, "", [{"title": title, "note": window_note, "columns": columns, "labels": labels,
                                        "rows": rows, "chart": chart}], now, logo=logo, headed=False)


def sections_to_pdf(title: str, note: str, sections: list[dict[str, Any]], now: datetime,
                    logo: Path | None = None, headed: bool = True) -> bytes:
    """Several tables in one PDF (a dashboard's tiles): per section its title, note, a bar chart
    when it is one label against one number (unless chart is False) and its table. `headed`
    adds the document's own title and note above the first section."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    size = landscape(letter) if any(len(sec["columns"]) > 5 for sec in sections) else letter
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    small = ParagraphStyle("cell", parent=body, fontSize=8, leading=10)

    def chrome(canvas, doc) -> None:
        canvas.saveState()
        top = size[1] - 0.5 * inch
        mark = logo or _LOGO   # the organization's own logo when it set one
        if mark.exists():
            canvas.drawImage(str(mark), 0.6 * inch, top - 0.3 * inch, height=0.3 * inch, width=1.1 * inch,
                             preserveAspectRatio=True, mask="auto")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(size[0] - 0.6 * inch, top - 0.2 * inch, title[:90])
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(0.6 * inch, 0.45 * inch, f"Generated {now:%d %b %Y %H:%M} UTC · Origin")
        canvas.drawRightString(size[0] - 0.6 * inch, 0.45 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def table_of(columns: list[str], labels: dict[str, str], rows: list[dict[str, Any]]):
        header = [Paragraph(xml_escape(labels.get(c, c)), ParagraphStyle("head", parent=small, textColor="white",
                                                                         fontName="Helvetica-Bold")) for c in columns]
        data = [header] + [[Paragraph(xml_escape(v), small) if isinstance(v, _Text) else v for v in r]
                           for r in _pdf_cells(columns, rows)]
        numbers = set(_number_columns(columns, rows))
        numeric = [i for i, c in enumerate(columns) if c in numbers]
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(_BRAND_BLUE)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5F8")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DDE5")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            *[("ALIGN", (i, 1), (i, -1), "RIGHT") for i in numeric],
        ]))
        return table

    # Paragraph reads its text as markup: escaped, a value is only ever text (an '&' broke the
    # PDF; '<link href=...>' in a cell became a live link).
    story = [Paragraph(xml_escape(title), styles["Heading1"]), Paragraph(xml_escape(note or ""), body),
             Spacer(1, 0.2 * inch)] if headed else []
    for sec in sections:
        columns, labels, rows = sec["columns"], sec.get("labels") or {}, sec.get("rows") or []
        story += [Paragraph(xml_escape(sec.get("title") or ""), styles["Heading2"]),
                  Paragraph(xml_escape(sec.get("note") or ""), body), Spacer(1, 0.15 * inch)]
        drawing = _bar_chart(columns, labels, rows, size[0] - 1.2 * inch) if sec.get("chart", True) and rows else None
        if drawing is not None:
            story += [drawing, Spacer(1, 0.2 * inch)]
        empty = [] if sec.get("failed") else [Paragraph("No rows in this window.", body)]
        story += [*([table_of(columns, labels, rows)] if rows else empty),
                  Spacer(1, 0.3 * inch)]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=size, topMargin=1.0 * inch, bottomMargin=0.8 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch, title=title)
    doc.build(story, onFirstPage=chrome, onLaterPages=chrome)
    return buf.getvalue()


def _message(schedule: dict[str, Any], columns: list[str], labels: dict[str, str],
             rows: list[dict[str, Any]], now: datetime):
    title = schedule.get("view_title") or schedule.get("snapshot_id") or "Report"
    fmt = schedule.get("format") or "csv"
    excel = fmt == "xlsx"
    msg = build_message(
        f"{title} — {now.date().isoformat()}",
        schedule.get("recipients", []),
        f"Scheduled report: {title}\n"
        f"{schedule.get('window_note') or ''}\n\n"
        f"The data is attached as {'Excel' if excel else 'a PDF report' if fmt == 'pdf' else 'CSV'}. "
        "Open the portal for the interactive view.\n")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(title))[:60] or "report"
    stem = f"{safe}_{now.date().isoformat()}"
    if fmt == "pdf":
        msg.add_attachment(rows_to_pdf(str(title), schedule.get("window_note") or "", columns, labels, rows, now,
                                       chart=True, logo=pdf_logo_path(schedule.get("organization_id"))),
                           maintype="application", subtype="pdf", filename=f"{stem}.pdf")
    elif excel:
        msg.add_attachment(rows_to_xlsx(columns, labels, rows), maintype="application",
                           subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           filename=f"{stem}.xlsx")
    else:
        msg.add_attachment(rows_to_csv(columns, labels, rows).encode("utf-8"), maintype="text",
                           subtype="csv", filename=f"{stem}.csv")
    return msg


HISTORY_KEEP = 20


def _record_run(schedule: dict[str, Any], now: datetime, trigger: str, status: str, rows: int | None) -> None:
    """Keep this run on the schedule, newest first, so "did it go out?" has an answer."""
    schedule["history"] = [{"at": now.isoformat(), "trigger": trigger, "status": status, "rows": rows},
                           *(schedule.get("history") or [])][:HISTORY_KEEP]
    _store.update(schedule)


def _failure(exc: Exception) -> str:
    from api.executive_dashboard import WAREHOUSE_NOT_BUILT_NOTE, is_missing_relation_error
    # the schedule dialog shows this: an unbuilt warehouse gets the sentence the dashboards
    # use rather than the driver's ORA-00942
    return WAREHOUSE_NOT_BUILT_NOTE if is_missing_relation_error(str(exc)) else f"error: {exc}"


def deliver(schedule: dict[str, Any], view: dict[str, Any], now: datetime,
            send: Callable[[Any], None], trigger: str | None = None) -> int:
    """Render and send one schedule; returns the row count delivered. With a trigger ("send
    now"), the run is also kept in the schedule's history, failed or not."""
    try:
        columns, labels, rows = render_schedule(schedule, view)
        send(_message(schedule, columns, labels, rows, now))
    except Exception as exc:
        if trigger:
            _record_run(schedule, now, trigger, _failure(exc), None)
        raise
    if trigger:
        _record_run(schedule, now, trigger, "sent", len(rows))
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
                _record_run(schedule, now, "schedule", "sent", count)
        except Exception as exc:  # noqa: BLE001 — the runner must survive any one failure
            reason = _failure(exc)
            result["status"] = reason
            schedule["last_status"] = reason
            _record_run(schedule, now, "schedule", reason, None)
        results.append(result)
    return results
