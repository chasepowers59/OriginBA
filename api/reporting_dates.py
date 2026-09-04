"""One "today" for every reporting window.

Four code paths built a "last N days" window and one of them disagreed:
report_schedules ended its window on `datetime.now(timezone.utc).date()` while
kpi_runner, nlq_metrics and snapshot_explorer all used `date.today()`. On a server
that is not UTC those differ for as many hours a day as the offset -- six, here --
and schedules run on an hourly cron, so a scheduled report's "last 30 days" ended a
day later than the same window on screen and the emailed number did not tie.

LOCAL is the correct basis. These windows filter BUSINESS dates -- Bill Date,
Accounting Date, Payment Date -- which are calendar dates in the utility's own
timezone, not UTC instants, so the outlier was also the wrong answer. It is invisible
on a UTC server, which is how it survived.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

# Two years. A window is a filter, not an export: a mistyped 99999 should not turn an
# interactive chart into a whole-warehouse scan.
MAX_WINDOW_DAYS = 730

# What an unfiltered canvas query falls back to. A quarter is the smallest span that
# still shows a billing cycle's shape.
DEFAULT_WINDOW_DAYS = 90

# The default window is applied only to canvases at least this big. Measured: the window
# takes Ellensburg RPT_GL (6.08M rows) from 4,062ms to 825ms and makes demo25's
# rpt_measurement (3.56M, dates clumped) slightly SLOWER; on rpt_customer_account (562
# rows) it cannot speed anything up and turned "accounts by class" into "accounts set
# up in the last 90 days" (one bar instead of five). Below this, an unfiltered query
# reads the whole canvas, which at this size is the cheap and correct thing.
DEFAULT_WINDOW_MIN_ROWS = 100_000


def window_date_field(snapshot: dict[str, Any]) -> str | None:
    """The date column a window applies to, or None if the canvas has no date.

    One rule with four callers: the explorer's default window, the KPI runner, NLQ
    metrics and scheduled reports. It once fell back through a mandatory-window field
    from the retired snapshot catalog first, and the copies of that fallback are what
    windowed some canvases and not others. The measured default is the only source now.
    """
    return snapshot.get("default_date_field") or None


def window_date_label(snapshot: dict[str, Any], field: str) -> str:
    """A date column's human name for copy a reader sees, falling back to the id
    itself: a sentence with a blank where the column should be is worse than an id."""
    for declared in (snapshot.get("date_fields") or []):
        if declared.get("id") == field and declared.get("label"):
            return str(declared["label"])
    return field


def reporting_today() -> date:
    """The calendar date the business is in."""
    return date.today()


def reporting_window(days: int, *, max_days: int = MAX_WINDOW_DAYS) -> tuple[str, str]:
    """(start, end) as ISO dates for a trailing window ending today.

    Clamped to at least one day so a zero or negative request cannot produce a window
    that ends before it starts -- an inverted BETWEEN returns nothing and looks like
    missing data rather than a bad parameter.
    """
    try:
        requested = int(days)
    except (TypeError, ValueError):
        requested = 1
    span = max(1, min(requested, max_days))
    end = reporting_today()
    return (end - timedelta(days=span)).isoformat(), end.isoformat()
