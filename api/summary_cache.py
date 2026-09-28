"""A five-minute cache for page summaries and report results, which change only when the
warehouse is rebuilt.

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
# Report results ride here too; the oldest entry goes first past this many.
MAX_ENTRIES = 500
_entries: dict[tuple, tuple[float, Any]] = {}
_lock = threading.Lock()


def _no_failed_card(result: Any) -> bool:
    return not any(k.get("error") for k in result.get("kpis") or []) and not result.get("error")


def cached(key: tuple, build: Callable[[], Any], keep: Callable[[Any], bool] = _no_failed_card) -> Any:
    full = (date.today().isoformat(), *key)
    with _lock:
        hit = _entries.get(full)
    if hit and time.monotonic() - hit[0] < TTL_SECONDS:
        return hit[1]
    result = build()
    if keep(result):
        with _lock:
            _entries[full] = (time.monotonic(), result)
            while len(_entries) > MAX_ENTRIES:
                _entries.pop(next(iter(_entries)))
    return result


def clear() -> None:
    with _lock:
        _entries.clear()
