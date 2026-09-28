"""A five-minute cache for page summaries, which change only when the warehouse is rebuilt.

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
_entries: dict[tuple, tuple[float, dict[str, Any]]] = {}
_lock = threading.Lock()


def cached(key: tuple, build: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    full = (date.today().isoformat(), *key)
    with _lock:
        hit = _entries.get(full)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    result = build()
    if not any(k.get("error") for k in result.get("kpis") or []) and not result.get("error"):
        with _lock:
            _entries[full] = (time.monotonic(), result)
    return result


def clear() -> None:
    with _lock:
        _entries.clear()
