"""A cache for page summaries and report results, which change only when the warehouse is
rebuilt. With the warehouse's build stamp (api/data_version.py) a result is kept until the
stamp moves, at most twelve hours; without one, five minutes.

The key is everything a summary depends on (org, window, comparison, filters, lenses, the
caller's grants, and the day, so a window never outlives its date). A summary with any
failed card is never kept: a transient error must not be served to the next visitor.
"""
from __future__ import annotations

import threading
import time
from datetime import date
from typing import Any, Callable

TTL_SECONDS = 300
VERSIONED_TTL_SECONDS = 12 * 3600
# Report results ride here too; the oldest entry goes first past this many.
MAX_ENTRIES = 500
_entries: dict[tuple, tuple[float, Any]] = {}
_lock = threading.Lock()
_counts = {"hits": 0, "misses": 0}


def _no_failed_card(result: Any) -> bool:
    return not any(k.get("error") for k in result.get("kpis") or []) and not result.get("error")


def cached(key: tuple, build: Callable[[], Any], keep: Callable[[Any], bool] = _no_failed_card,
           version: str | None = None) -> Any:
    full = (date.today().isoformat(), version, *key)
    ttl = VERSIONED_TTL_SECONDS if version else TTL_SECONDS
    with _lock:
        hit = _entries.get(full)
    if hit and time.monotonic() - hit[0] < ttl:
        _counts["hits"] += 1
        return hit[1]
    _counts["misses"] += 1
    result = build()
    if keep(result):
        with _lock:
            _entries[full] = (time.monotonic(), result)
            while len(_entries) > MAX_ENTRIES:
                _entries.pop(next(iter(_entries)))
    return result


def stats() -> dict[str, int]:
    with _lock:
        return {**_counts, "entries": len(_entries)}


def clear() -> None:
    with _lock:
        _entries.clear()
        _counts.update(hits=0, misses=0)
