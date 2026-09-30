"""The explorer's opening date window, as the browser computes it (datePresets.ts:
applyDatePresetConfig). Kept in step by tests/fixtures/date_presets.json, which both test
suites read; the cache warmer uses it to run the report a page will ask for."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any


# a canvas may name its default: the name picks the explorer's chip of that label
NAMED = {
    "last_30_days": {"kind": "days", "days": 30},
    "last_quarter": {"kind": "days", "days": 90},
    "prior_month": {"kind": "last_month"},
    "year_to_date": {"kind": "ytd"},
    "last_12_months": {"kind": "days", "days": 365},
}


def preset_range(preset: dict[str, Any] | str | None, end: date) -> list[str]:
    p = (NAMED.get(preset) if isinstance(preset, str) else preset) or {"kind": "days", "days": 180}
    if p.get("kind") == "ytd":
        start = date(end.year, 1, 1)
    elif p.get("kind") == "last_month":
        end = end.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
    else:
        start = end - timedelta(days=int(p.get("days") or 180))
    return [start.isoformat(), end.isoformat()]


# The chip labels a saved view stores (ExplorerPanel DATE_PRESETS, widenDateRange, the default).
_LABEL_PRESETS = {
    "Last 30 days": {"kind": "days", "days": 30},
    "Last quarter": {"kind": "days", "days": 90},
    "Prior month": {"kind": "last_month"},
    "Year to date": {"kind": "ytd"},
    "Last 6 months": {"kind": "days", "days": 180},
    "Last 12 months": {"kind": "days", "days": 365},
    "Last 24 months": {"kind": "days", "days": 730},
}


def saved_window(label: str | None, start: str | None, end: str | None, as_of: date) -> list[str] | None:
    """What a saved view's window means now: a named window stays relative to the data's end,
    a custom range stays fixed, "All dates" has none."""
    if label == "All dates":
        return None
    days = re.fullmatch(r"Last (\d+) days", label or "")
    preset = _LABEL_PRESETS.get(label or "") or ({"kind": "days", "days": int(days.group(1))} if days else None)
    if preset:
        return preset_range(preset, as_of)
    return [start, end] if start and end else None

