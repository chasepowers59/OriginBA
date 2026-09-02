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
# still shows a billing cycle's shape, and it is what the legacy snapshots have always
# applied -- this is the existing behaviour given one home, not a new policy.
DEFAULT_WINDOW_DAYS = 90


def window_date_field(snapshot: dict[str, Any]) -> str | None:
    """The date column a window should apply to, or None if the canvas has no date.

    `required_date_field` ALONE is a CISADM-era read: no dbt canvas declares one, so
    every consumer that checked only that field silently stopped windowing on the 38
    canvas-backed snapshots while continuing to window the 19 legacy ones. It caused
    opposite bugs in the two shapes -- a scheduled report emailed the whole table under
    a "trailing 30 days" heading, and an unfiltered canvas query scanned every row --
    and it was found and fixed three separate times before this became one function.
    """
    return snapshot.get("required_date_field") or snapshot.get("default_date_field") or None


def window_date_label(snapshot: dict[str, Any], field: str) -> str:
    """A date column's HUMAN name, for copy that a reader sees.

    The two shapes name their columns differently and only one of them needs
    translating: a dbt canvas field is already Title Case ("Bill Date"), while a legacy
    snapshot's is a database column ("ACCOUNTING_DT") whose label is "Accounting date".
    Six of nine orgs are legacy, so printing the raw id would be the majority
    experience. Falls back to the id itself rather than to nothing -- a sentence with a
    blank where the column should be is worse than an ugly column name.
    """
    if snapshot.get("required_date_field") == field and snapshot.get("required_date_label"):
        return str(snapshot["required_date_label"])
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
