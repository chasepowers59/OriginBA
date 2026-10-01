"""What Ori says unprompted about the home cards: findings, unusual months, projections, a read.

FINDINGS and ORI'S READ come from the SAME summary the home page shows (the vetted KPI
runner, compare mode), so they can never disagree with a card. A finding needs a windowed
card (a balance or a population has no prior period), both values present, a non-zero
prior, a move of at least 15%, and enough behind it to matter: a count of at least 20 or
money of at least 1,000 in either period. At most three, largest first.

UNUSUAL MONTHS and PROJECTIONS read each card's monthly history (api/ori_series.py). A month
is unusual only when it falls outside all of the 12 before it AND sits 3.5 robust deviations
and 15% from their median (a seasonal peak inside last year's range is not news). A
projection of the next three months is either the same months last year scaled by the last
three months against a year earlier, or the average of the last 12 months: whichever missed
the three-month total less when replayed on the organization's own past months, published
only when that miss was at most 15% in a typical case and at most 25% in four cases of five,
over at least 8 checks; its range is that 80th-percentile past miss.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any

MIN_CHANGE_PCT = 15.0   # 25% missed Ellensburg billed revenue down 17.9% ($733K), 2026-09-29
MIN_COUNT = 20
MIN_MONEY = 1000.0
MAX_FINDINGS = 3
MODERATE_PCT = 5.0

BASELINE_MONTHS = 12
ROBUST_Z = 3.5          # Iglewicz and Hoaglin's modified z-score cut-off
MAX_ANOMALIES = 3

HORIZON = 3
MAX_TYPICAL_MISS_PCT = 15.0
MAX_RANGE_PCT = 25.0    # Ellensburg field activities passed the typical miss at 11% with a +-43% range
MIN_CHECKS = 8
RANGE_PERCENTILE = 0.8


def _amount(value: float, fmt: str) -> str:
    return f"{'-' if value < 0 else ''}${abs(value):,.2f}" if fmt == "currency" else f"{value:,.0f}"


def _approx(value: float, fmt: str) -> str:
    """An estimate, as format.ts formatCompact writes a headline: 3 significant digits from 10,000."""
    if abs(value) < 10_000:
        return _amount(value, fmt)
    rounded = float(f"{abs(value):.3g}")
    size, suffix = next((s, x) for s, x in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")) if rounded >= s)
    scaled = rounded / size
    digits = f"{scaled:.{max(0, 2 - int(math.log10(scaled)))}f}"
    digits = digits.rstrip("0").rstrip(".") if "." in digits else digits
    return f"{'-' if value < 0 else ''}{'$' if fmt == 'currency' else ''}{digits}{suffix}"


def findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for k in summary.get("kpis") or []:
        now, before, change = k.get("value"), k.get("prior_value"), k.get("change_pct")
        if k.get("error") or not k.get("compare_label") or None in (now, before, change) or not before:
            continue
        if abs(change) < MIN_CHANGE_PCT or max(abs(now), abs(before)) < _floor(k.get("format")):
            continue
        direction = "up" if change > 0 else "down"
        label, fmt = k.get("label") or k.get("id"), k.get("format") or "number"
        out.append({
            "kpi_id": k.get("id"),
            "change_pct": change,
            # "label: down 18%" reads right for a plural label ("Usage transactions") as well
            "headline": f"{label}: {direction} {abs(change):.0f}% {k['compare_label']}",
            "detail": f"{_amount(now, fmt)} now, {_amount(before, fmt)} before.",
            "question": f"Why did {_lower_first(label)} go {direction} {abs(change):.0f}% {k['compare_label']}? "
                        "What changed?",
        })
    return sorted(out, key=lambda f: -abs(f["change_pct"]))[:MAX_FINDINGS]


_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _month_label(month: str) -> str:
    y, m = month.split("-")
    return f"{_MONTHS[int(m) - 1]} {y}"


def _span_label(first: str, last: str) -> str:
    a, b = _month_label(first), _month_label(last)
    return f"{a.split()[0]} to {b}" if a[-4:] == b[-4:] else f"{a} to {b}"


def _next_month(month: str, ahead: int) -> str:
    y, m = map(int, month.split("-"))
    total = y * 12 + (m - 1) + ahead
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _floor(fmt: str) -> float:
    return MIN_MONEY if fmt == "currency" else MIN_COUNT


def _lower_first(label: str) -> str:
    """Mid-sentence case: "Billed revenue" -> "billed revenue"; an acronym ("GL lines") or a name
    ("To Do entries", its second word capitalised too) keeps its capital."""
    words = label.split()
    if len(label) < 2 or not label[1].islower() or (len(words) > 1 and words[1][:1].isupper()):
        return label
    return label[0].lower() + label[1:]


def anomalies(history: dict[str, list[dict[str, Any]]], meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for kpi_id, points in history.items():
        if len(points) < BASELINE_MONTHS + 1:
            continue
        latest = points[-1]
        x, base = latest["value"], [p["value"] for p in points[-BASELINE_MONTHS - 1:-1]]
        typical, lo, hi = median(base), min(base), max(base)
        fmt, label = meta[kpi_id]["format"], meta[kpi_id]["label"]
        if lo <= x <= hi or max(abs(x), abs(typical)) < _floor(fmt):
            continue
        if not typical or abs(x - typical) / abs(typical) * 100 < MIN_CHANGE_PCT:
            continue
        spread = median(abs(v - typical) for v in base)
        z = math.inf if spread == 0 else 0.6745 * abs(x - typical) / spread
        if z < ROBUST_Z:
            continue
        high, month = x > hi, _month_label(latest["month"])
        out.append({
            "kpi_id": kpi_id, "snapshot_id": meta[kpi_id].get("snapshot_id"),
            "month": latest["month"],
            "direction": "high" if high else "low",
            "z": z,
            "headline": f"{label} for {month}: unusually {'high' if high else 'low'}",
            "detail": f"{_amount(x, fmt)}, {'above' if high else 'below'} every one of the {BASELINE_MONTHS} months "
                      f"before ({_amount(lo, fmt)} to {_amount(hi, fmt)}; typical {_amount(typical, fmt)}).",
            "question": f"What made {_lower_first(label)} so {'high' if high else 'low'} in {month}? "
                        "What changed from the months before?",
        })
    out.sort(key=lambda a: -a["z"])
    return [{k: v for k, v in a.items() if k != "z"} for a in out[:MAX_ANOMALIES]]


def _seasonal(values: list[float], origin: int, ahead: int) -> float | None:
    """Month origin+ahead from the months up to origin: last year's month times recent growth."""
    recent, year_ago = values[origin - 2:origin + 1], values[origin - 14:origin - 11]
    if origin < 14 or sum(year_ago) <= 0 or min(year_ago) < 0:
        return None
    return values[origin + ahead - 12] * sum(recent) / sum(year_ago)


def _average(values: list[float], origin: int, ahead: int) -> float | None:
    return sum(values[origin - 11:origin + 1]) / 12 if origin >= 11 else None


# Tried in order, the better past record wins (a tie keeps the seasonal one)
METHODS = ((_seasonal, "Built from the same months last year, scaled by how the last three months compared "
                       "with a year earlier"),
           (_average, "Built from the average of the last 12 months"))


def _replay(values: list[float], method) -> tuple[list[float], list[float]]:
    """The method's relative misses on the organization's own past: each month, and each three-month total."""
    months, totals = [], []
    for origin in range(14, len(values) - 1):
        guesses = [method(values, origin, a) for a in range(1, HORIZON + 1) if origin + a < len(values)]
        actual = values[origin + 1:origin + 1 + len(guesses)]
        if None in guesses:
            continue
        months += [abs(g - v) / v for g, v in zip(guesses, actual) if v > 0]
        if len(guesses) == HORIZON and sum(actual) > 0:
            totals.append(abs(sum(guesses) - sum(actual)) / sum(actual))
    return months, totals


def _p80(misses: list[float]) -> float:
    return sorted(misses)[max(0, math.ceil(RANGE_PERCENTILE * len(misses)) - 1)]


def forecasts(history: dict[str, list[dict[str, Any]]], meta: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """The next three months. What is tested, gated and stated is the three-month TOTAL: payments
    slip between months (Ellensburg: single months missed by ~15%, three-month totals by 9%)."""
    out = []
    for kpi_id, points in history.items():
        values, best = [p["value"] for p in points], None
        for method, how in METHODS:
            months, totals = _replay(values, method)
            projected = [method(values, len(values) - 1, a) for a in range(1, HORIZON + 1)]
            if (len(totals) >= MIN_CHECKS and None not in projected
                    and median(totals) * 100 <= MAX_TYPICAL_MISS_PCT and _p80(totals) * 100 <= MAX_RANGE_PCT
                    and (best is None or median(totals) < best[0])):
                best = (median(totals), months, totals, projected, how)
        if best is None:
            continue
        typical, months, totals, projected, how = best[0] * 100, *best[1:]
        band = _p80(months)
        ahead = [_next_month(points[-1]["month"], a) for a in range(1, HORIZON + 1)]
        rows = [{"month": m, "value": v, "low": max(0.0, v * (1 - band)), "high": v * (1 + band)}
                for m, v in zip(ahead, projected)]
        total = sum(projected)
        low, high = max(0.0, total * (1 - _p80(totals))), total * (1 + _p80(totals))
        fmt, label, span = meta[kpi_id]["format"], meta[kpi_id]["label"], _span_label(ahead[0], ahead[-1])
        out.append({
            "kpi_id": kpi_id, "label": label, "format": fmt, "snapshot_id": meta[kpi_id].get("snapshot_id"),
            "history": points[-BASELINE_MONTHS:], "forecast": rows,
            "total": total, "total_low": low, "total_high": high,
            "typical_error_pct": typical, "checks": len(totals),
            "headline": f"{label}: about {_approx(total, fmt)} over {span}",
            "detail": f"Likely between {_approx(low, fmt)} and {_approx(high, fmt)}. {how}; replayed on past "
                      f"months, its three-month total was off by {typical:.0f}% in a typical case "
                      f"({len(totals)} checks).",
            "question": f"What is driving the {_lower_first(label)} forecast for {span}?",
        })
    return out


def _moved(k: dict[str, Any]) -> str:
    return f"{_lower_first(k['label'])} {'rose' if k['change_pct'] > 0 else 'fell'} {abs(k['change_pct']):.0f}%"


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"


def brief(summary: dict[str, Any]) -> str | None:
    """Ori's read of the period: big moves, then moderate ones, then the steady cards together."""
    cards = [k for k in summary.get("kpis") or []
             if not k.get("error") and k.get("compare_label") and k.get("change_pct") is not None]
    if not cards:
        return None
    period = summary.get("period") or {}
    # the findings' volume floors: a 200% rise on three bills is not a move worth naming
    thin = [k for k in cards if max(abs(k.get("value") or 0), abs(k.get("prior_value") or 0)) < _floor(k.get("format"))]
    cards = [k for k in cards if k not in thin]
    by_size = sorted(cards, key=lambda k: -abs(k["change_pct"]))
    big = [_moved(k) for k in by_size if abs(k["change_pct"]) >= MIN_CHANGE_PCT]
    moderate = [_moved(k) for k in by_size if MODERATE_PCT <= abs(k["change_pct"]) < MIN_CHANGE_PCT]
    steady = [_lower_first(k["label"]) for k in cards if abs(k["change_pct"]) < MODERATE_PCT]
    before = f"the {period.get('days', 30)} days before"
    clauses = [f"{_join(big)} against {before}" if big else None,
               f"{_join(moderate)}" + ("" if big else f" against {before}") if moderate else None,
               f"{_join(steady)} held within {MODERATE_PCT:.0f}%" + ("" if big or moderate else f" of {before}")
               if steady else None,
               f"{_join([_lower_first(k['label']) for k in thin])} had too little activity to compare" if thin else None]
    clauses = [c for c in clauses if c]
    lead = f"In the {_lower_first(period.get('label') or 'period')}, {clauses[0]}."
    return " ".join([lead] + [f"{c[0].upper()}{c[1:]}." for c in clauses[1:]])


def grounding(kind: str, kpi_id: str, history: dict[str, list[dict[str, Any]]],
              meta: dict[str, dict[str, Any]]) -> str | None:
    """What Ori showed for one item, restated for the assistant from the same history. Without
    it a question about a forecast reached a model told never to state a figure no data set
    holds, and it answered that no forecast exists (2026-10-01)."""
    if kpi_id not in history or kpi_id not in meta:
        return None
    one = {kpi_id: history[kpi_id]}
    if kind == "forecast":
        found = forecasts(one, meta)
        if not found:
            return None
        f, fmt = found[0], meta[kpi_id]["format"]
        months = "; ".join(f"{_month_label(p['month'])} about {_approx(p['value'], fmt)} "
                           f"(likely {_approx(p['low'], fmt)} to {_approx(p['high'], fmt)})" for p in f["forecast"])
        return (f"Ori's forecast on the Forecasts page, computed by the portal from the monthly history of the "
                f"{f['label']} card through {_month_label(history[kpi_id][-1]['month'])} (it is not a data set): "
                f"{f['headline']}. {f['detail']} By month: {months}. Explain what drives it from that history "
                f"(query the months it is built on); it is an estimate, not a figure in the data.")
    if kind == "anomaly":
        found = anomalies(one, meta)
        if not found:
            return None
        a = found[0]
        return f"Ori flagged this on Home from the {meta[kpi_id]['label']} card's monthly history: {a['headline']}. {a['detail']}"
    return None
