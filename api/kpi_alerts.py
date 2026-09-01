"""KPI threshold alerts — the executive dashboard watching itself.

An alert subscribes recipients to ONE executive KPI with a condition: the value
crossing a threshold, or the period-over-period change moving too far. The hourly
runner evaluates each alert through the SAME kpi_runner the dashboard uses, so an
alert can never disagree with the tile it watches.

Notification fires only on the TRANSITION into breach — a KPI that stays red all
week sends one email, not seven. Recovery resets last_state so the next breach
notifies again.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api.executive_dashboard import EXECUTIVE_KPIS
from api.notifications import build_message, clean_recipients, send_message
from api.org_store import OrgRecordStore

ROOT = Path(__file__).resolve().parent.parent
ALERTS_PATH = ROOT / "data" / "analytics_portal" / "kpi_alerts.json"
MAX_ALERTS = 20
CONDITIONS = ("above", "below", "pct_change_above", "pct_change_below")

_store = OrgRecordStore("kpi_alerts", lambda: ALERTS_PATH, "alerts")


class AlertError(ValueError):
    pass


def _kpi_by_id(kpi_id: str) -> dict[str, Any] | None:
    return next((k for k in EXECUTIVE_KPIS if k["id"] == kpi_id), None)


def watchable_kpis() -> list[dict[str, Any]]:
    return [{"id": k["id"], "label": k["label"], "subtitle": k.get("subtitle", ""),
             "format": k.get("format", "number")} for k in EXECUTIVE_KPIS]


def list_alerts(organization_id: str) -> list[dict[str, Any]]:
    return _store.list(organization_id)


def create_alert(payload: dict[str, Any], *, organization_id: str,
                 created_by: str) -> dict[str, Any]:
    kpi = _kpi_by_id(str(payload.get("kpi_id") or ""))
    if kpi is None:
        raise AlertError("Unknown KPI")
    condition = str(payload.get("condition") or "")
    if condition not in CONDITIONS:
        raise AlertError(f"Condition must be one of {', '.join(CONDITIONS)}")
    assert_condition_can_fire(str(payload.get("kpi_id") or ""), condition)
    try:
        threshold = float(payload.get("threshold"))
    except (TypeError, ValueError) as exc:
        raise AlertError("Threshold must be a number") from exc
    try:
        recipients = clean_recipients(payload.get("recipients"))
    except ValueError as exc:
        raise AlertError(str(exc)) from exc
    window_days = int(payload.get("window_days") or 7)
    if not 1 <= window_days <= 366:
        raise AlertError("window_days must be 1-366")
    if len(list_alerts(organization_id)) >= MAX_ALERTS:
        raise AlertError(f"Alert limit reached ({MAX_ALERTS} per organization)")

    return _store.add({
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
    })


def delete_alert(alert_id: str, organization_id: str) -> bool:
    return _store.delete(alert_id, organization_id)


def assert_condition_can_fire(kpi_id: str, condition: str) -> None:
    """Refuse a period-over-period condition on a point-in-time KPI.

    Four executive KPIs are WINDOWLESS stock metrics -- a balance or a population has no
    prior period, so the runner returns change_pct=None every run and
    evaluate_condition correctly never breaches on None. The alert saved, looked
    configured, and could not fire in principle. Refusing here puts the answer where
    there is somebody to read it.

    Threshold conditions stay available on stock metrics: "tell me when past-due balance
    goes above X" is exactly the question worth asking of a balance.
    """
    if not condition.startswith("pct_change"):
        return
    kpi = _kpi_by_id(kpi_id)
    if kpi is None or not kpi.get("windowless"):
        return
    label = kpi.get("label", kpi_id)
    raise AlertError(
        f"{label} is a point-in-time total, so it has no period to compare against and a "
        "percent-change alert could never fire. Use an above or below threshold instead."
    )


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


def _window_phrase(alert: dict[str, Any]) -> str:
    """A stock metric is as-of, not trailing; saying "trailing 7 days" of a balance
    describes a window that was never applied."""
    kpi = _kpi_by_id(alert.get("kpi_id", ""))
    if kpi is not None and kpi.get("windowless"):
        return " (point-in-time total)"
    return f" (trailing {alert.get('window_days', 7)} days)"


def _message(alert: dict[str, Any], result: dict[str, Any], now: datetime):
    label = alert.get("kpi_label") or alert["kpi_id"]
    pct = result.get("pct_change")
    unit = "%" if alert["condition"].startswith("pct_change") else ""
    return build_message(
        f"KPI alert: {label} — {now.date().isoformat()}",
        alert.get("recipients", []),
        f"{label} {_CONDITION_TEXT.get(alert['condition'], alert['condition'])} "
        f"{alert['threshold']}{unit}.\n\n"
        f"Current value{_window_phrase(alert)}: {result.get('value')}\n"
        + (f"Period-over-period change: {pct:.1f}%\n" if pct is not None else "")
        + "\nOpen the portal's executive overview for the full picture.\n")


def run_kpi_alerts(*, now: datetime | None = None,
                   send: Callable[[Any], None] | None = None) -> list[dict[str, Any]]:
    """Evaluate every enabled alert; notify only on the transition into breach."""
    now = now or datetime.now(timezone.utc)
    send = send or send_message
    results: list[dict[str, Any]] = []
    for alert in _store.list_all():
        if not alert.get("enabled", True):
            continue
        result = {"id": alert["id"], "kpi": alert.get("kpi_label"),
                  "recipients": alert.get("recipients", [])}
        try:
            kpi = _kpi_result(alert)
            value = kpi.get("value")
            breached = evaluate_condition(
                alert["condition"], float(alert["threshold"]),
                value=value, pct_change=kpi.get("pct_change"))
            alert["last_checked_at"] = now.isoformat()
            alert["last_value"] = value
            if breached and alert.get("last_state") != "breached":
                send(_message(alert, kpi, now))
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
            _store.update(alert)
        except Exception as exc:  # noqa: BLE001 — one failure never blocks the rest
            result["status"] = f"error: {exc}"
            alert["last_status"] = f"error: {exc}"
            _store.update(alert)
        results.append(result)
    return results
