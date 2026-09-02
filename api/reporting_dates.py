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

# Two years. A window is a filter, not an export: a mistyped 99999 should not turn an
# interactive chart into a whole-warehouse scan.
MAX_WINDOW_DAYS = 730


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
