"""Ori's findings: the large moves in the home cards, compared with the prior period.

Built from the SAME summary the home page shows (the vetted KPI runner, compare mode), so a
finding can never disagree with its card. A finding needs a windowed card (a balance or a
population has no prior period), both values present, a non-zero prior, a move of at least
15%, and enough behind it to matter: a count of at least 20 or money of at least 1,000 in
either period. At most three, largest first.
"""
from __future__ import annotations

from typing import Any

MIN_CHANGE_PCT = 15.0   # 25% missed Ellensburg billed revenue down 17.9% ($733K), 2026-09-29
MIN_COUNT = 20
MIN_MONEY = 1000.0
MAX_FINDINGS = 3


def _amount(value: float, fmt: str) -> str:
    return f"{'-' if value < 0 else ''}${abs(value):,.2f}" if fmt == "currency" else f"{value:,.0f}"


def findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for k in summary.get("kpis") or []:
        now, before, change = k.get("value"), k.get("prior_value"), k.get("change_pct")
        if k.get("error") or not k.get("compare_label") or None in (now, before, change) or not before:
            continue
        floor = MIN_MONEY if k.get("format") == "currency" else MIN_COUNT
        if abs(change) < MIN_CHANGE_PCT or max(abs(now), abs(before)) < floor:
            continue
        direction = "up" if change > 0 else "down"
        label, fmt = k.get("label") or k.get("id"), k.get("format") or "number"
        out.append({
            "kpi_id": k.get("id"),
            "change_pct": change,
            "headline": f"{label} is {direction} {abs(change):.0f}% {k['compare_label']}",
            "detail": f"{_amount(now, fmt)} now, {_amount(before, fmt)} before.",
            "question": f"Why is {label} {direction} {abs(change):.0f}% {k['compare_label']}? What changed?",
        })
    return sorted(out, key=lambda f: -abs(f["change_pct"]))[:MAX_FINDINGS]
