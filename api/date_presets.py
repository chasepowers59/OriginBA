"""The explorer's opening date window, as the browser computes it (datePresets.ts:
applyDatePresetConfig). Kept in step by tests/fixtures/date_presets.json, which both test
suites read; the cache warmer uses it to run the report a page will ask for."""
from __future__ import annotations

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
