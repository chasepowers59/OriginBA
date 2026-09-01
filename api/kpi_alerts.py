"""KPI threshold alerts — the executive dashboard that watches itself.

An alert subscribes recipients to ONE executive KPI with a condition: the value
crossing a threshold, or the period-over-period change moving too far. The hourly
runner evaluates each alert through the SAME kpi_runner the dashboard uses, so an
alert can never disagree with the tile it watches.

Notification fires only on the TRANSITION into breach — a KPI that stays red all
week sends one email, not seven. Recovery is recorded silently on the alert's
last_state so the next breach notifies again.

Storage and SMTP follow report_schedules.py (portal_state / local JSON; SMTP_*).
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api import portal_state_store as _pss
from api.executive_dashboard import EXECUTIVE_KPIS
from api.report_schedules import _EMAIL_RE, smtp_configured, _smtp_send

ROOT = Path(__file__).resolve().parent.parent
ALERTS_PATH = ROOT / "data" / "analytics_portal" / "kpi_alerts.json"
_COLLECTION = "kpi_alerts"
MAX_ALERTS = 20
CONDITIONS = ("above", "below", "pct_change_above", "pct_change_below")


class AlertError(ValueError):
    pass


def _kpi_by_id(kpi_id: str) -> dict[str, Any] | None:
    return next((k for k in EXECUTIVE_KPIS if k["id"] == kpi_id), None)


def watchable_kpis() -> list[dict[str, Any]]:
    return [{"id": k["id"], "label": k["label"], "subtitle": k.get("subtitle", ""),
             "format": k.get("format", "number")} for k in EXECUTIVE_KPIS]


# --- store -------------------------------------------------------------------------

def _load_store() -> dict[str, Any]:
    if ALERTS_PATH.exists():
        return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    return {"alerts": []}


def _save_store(data: dict[str, Any]) -> None:
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALERTS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_alerts(organization_id: str) -> list[dict[str, Any]]:
    if _pss.enabled():
        return _pss.list_records(_COLLECTION, organization_id)
    return [a for a in _load_store().get("alerts", [])
            if a.get("organization_id") == organization_id]


def _all_alerts() -> list[dict[str, Any]]:
    if _pss.enabled():
        return _pss.list_all_records(_COLLECTION)
    return list(_load_store().get("alerts", []))


def create_alert(payload: dict[str, Any], *, organization_id: str,
                 created_by: str) -> dict[str, Any]:
    kpi = _kpi_by_id(str(payload.get("kpi_id") or ""))
    if kpi is None:
        raise AlertError("Unknown KPI")
    condition = str(payload.get("condition") or "")
    if condition not in CONDITIONS:
        raise AlertError(f"Condition must be one of {', '.join(CONDITIONS)}")
    try:
        threshold = float(payload.get("threshold"))
    except (TypeError, ValueError) as exc:
        raise AlertError("Threshold must be a number") from exc
    recipients = [str(r).strip().lower() for r in (payload.get("recipients") or [])]
    if not recipients:
        raise AlertError("At least one recipient is required")
    for r in recipients:
        if not _EMAIL_RE.match(r):
            raise AlertError(f"Not a valid email address: {r}")
    window_days = int(payload.get("window_days") or 7)
    if not 1 <= window_days <= 366:
        raise AlertError("window_days must be 1-366")
    if len(list_alerts(organization_id)) >= MAX_ALERTS:
        raise AlertError(f"Alert limit reached ({MAX_ALERTS} per organization)")

    entry = {
        "id": str(uuid.uuid4()),
        "organization_id": organization_id,
        "kpi_id": kpi["id"],
        "kpi_label": kpi["label"],
        "condition": condition,
        "threshold": threshold,
        "window_days": window_days,
        "recipients": recipients,
        "enabled": True,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_state": "ok",
        "last_checked_at": None,
        "last_value": None,
        "last_status": None,
    }
    if _pss.enabled():
        _pss.upsert(_COLLECTION, entry["id"], organization_id, entry)
    else:
        store = _load_store()
        store.setdefault("alerts", []).append(entry)
        _save_store(store)
    return entry


def delete_alert(alert_id: str, organization_id: str) -> bool:
    if _pss.enabled():
        return _pss.delete(_COLLECTION, alert_id, organization_id)
    store = _load_store()
    before = len(store.get("alerts", []))
    store["alerts"] = [
        a for a in store.get("alerts", [])
        if not (a.get("id") == alert_id and a.get("organization_id") == organization_id)]
    if len(store["alerts"]) == before:
        return False
    _save_store(store)
    return True


def _update_alert(entry: dict[str, Any]) -> None:
    if _pss.enabled():
        _pss.upsert(_COLLECTION, entry["id"], entry["organization_id"], entry)
        return
    store = _load_store()
    store["alerts"] = [entry if a.get("id") == entry["id"] else a
                       for a in store.get("alerts", [])]
    _save_store(store)


# --- evaluation (pure) -------------------------------------------------------------

def evaluate_condition(condition: str, threshold: float, *,
                       value: float | None, pct_change: float | None) -> bool:
    """No data never breaches — an empty warehouse is a data problem, not a KPI one."""
    if condition == "above":
        return value is not None and value > threshold
    if condition == "below":
        return value is not None and value < threshold
    if condition == "pct_change_above":
        return pct_change is not None and pct_change > threshold
    if condition == "pct_change_below":
        return pct_change is not None and pct_change < threshold
    return False


# --- runner ------------------------------------------------------------------------

def _kpi_result(alert: dict[str, Any]) -> dict[str, Any]:
    """The alert's KPI, computed exactly as the dashboard computes it."""
    from api.kpi_runner import execute_kpi_definition

    kpi = _kpi_by_id(alert["kpi_id"])
    if kpi is None:
        raise AlertError("KPI no longer exists")
    return execute_kpi_definition(
        kpi, days=int(alert.get("window_days") or 7), compare=True,
        organization_id=alert["organization_id"])


_CONDITION_TEXT = {
    "above": "rose above",
    "below": "fell below",
    "pct_change_above": "changed period-over-period by more than",
    "pct_change_below": "changed period-over-period by less than",
}


def _build_alert_message(alert: dict[str, Any], result: dict[str, Any], now: datetime):
    from email.message import EmailMessage
    import os

    msg = EmailMessage()
    label = alert.get("kpi_label") or alert["kpi_id"]
    msg["Subject"] = f"KPI alert: {label} — {now.date().isoformat()}"
    msg["From"] = (os.environ.get("SMTP_FROM") or "reports@originba.local").strip()
    msg["To"] = ", ".join(alert.get("recipients", []))
    value = result.get("value")
    pct = result.get("pct_change")
    cond = _CONDITION_TEXT.get(alert["condition"], alert["condition"])
    unit = "%" if alert["condition"].startswith("pct_change") else ""
    msg.set_content(
        f"{label} {cond} {alert['threshold']}{unit}.\n\n"
        f"Current value (trailing {alert.get('window_days', 7)} days): {value}\n"
        + (f"Period-over-period change: {pct:.1f}%\n" if pct is not None else "")
        + "\nOpen the portal's executive overview for the full picture.\n")
    return msg


def run_kpi_alerts(*, now: datetime | None = None,
                   send: Callable[[Any], None] | None = None) -> list[dict[str, Any]]:
    """Evaluate every enabled alert; notify only on the transition into breach."""
    now = now or datetime.now(timezone.utc)
    send = send or _smtp_send
    results: list[dict[str, Any]] = []
    for alert in _all_alerts():
        if not alert.get("enabled", True):
            continue
        result = {"id": alert["id"], "kpi": alert.get("kpi_label"),
                  "recipients": alert.get("recipients", [])}
        try:
            kpi = _kpi_result(alert)
            value, pct = kpi.get("value"), kpi.get("pct_change")
            breached = evaluate_condition(
                alert["condition"], float(alert["threshold"]), value=value, pct_change=pct)
            alert["last_checked_at"] = now.isoformat()
            alert["last_value"] = value
            was_breached = alert.get("last_state") == "breached"
            if breached and not was_breached:
                send(_build_alert_message(alert, kpi, now))
                result["status"] = "breached-notified"
                alert["last_state"] = "breached"
                alert["last_status"] = f"notified at {value}"
            elif breached:
                result["status"] = "breached-quiet"
                alert["last_status"] = f"still breached at {value}"
            else:
                result["status"] = "ok"
                alert["last_state"] = "ok"
                alert["last_status"] = f"ok at {value}"
            _update_alert(alert)
        except Exception as exc:  # noqa: BLE001 — one failure never blocks the rest
            result["status"] = f"error: {exc}"
            alert["last_status"] = f"error: {exc}"
            _update_alert(alert)
        results.append(result)
    return results
