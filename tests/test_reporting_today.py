"""Every window must end on the same "today".

Four code paths build a "last N days" window and three of them agreed:

    kpi_runner.py:193        today = date.today()              # server local
    nlq_metrics.py:41        end   = date.today()              # server local
    snapshot_explorer.py:131 end   = date.today()              # server local
    report_schedules.py:127  end   = datetime.now(timezone.utc).date()   # UTC

On this machine (UTC-6) those two answers differ for SIX HOURS of every day, from
18:00 local until midnight. Schedules run on an hourly cron, so during that window a
scheduled report's "last 30 days" ends a day later than the same window on the
dashboard, and the emailed number does not tie to the screen. It is invisible on a
UTC server, which is why it survived: production may be UTC while a developer's
machine, or a self-hosted deployment, is not.

LOCAL is the right basis, not UTC. The columns these windows filter are BUSINESS
dates -- Bill Date, Accounting Date, Payment Date -- which are calendar dates in the
utility's own timezone, not UTC instants. Comparing a business date against a UTC
"today" is the less correct of the two, so the outlier is also the wrong one.

The rule now lives in one function. Two implementations of one rule is the shape that
also produced saveView vs buildRequest and the workstream filters.
"""

from __future__ import annotations

import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.reporting_dates import reporting_today, reporting_window  # noqa: E402


class ReportingTodayTests(unittest.TestCase):
    def test_it_is_the_calendar_date_the_business_is_in(self):
        self.assertEqual(reporting_today(), date.today())

    def test_it_returns_a_date_not_a_datetime(self):
        self.assertIsInstance(reporting_today(), date)


class ReportingWindowTests(unittest.TestCase):
    def test_a_window_ends_today_and_spans_the_days_asked_for(self):
        start, end = reporting_window(30)
        self.assertEqual(end, date.today().isoformat())
        self.assertEqual(start, (date.today() - timedelta(days=30)).isoformat())

    def test_iso_strings_because_that_is_what_the_filters_carry(self):
        start, end = reporting_window(7)
        for value in (start, end):
            self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$")

    def test_a_nonsense_window_is_clamped_rather_than_inverted(self):
        start, end = reporting_window(0)
        self.assertLessEqual(start, end)
        start, end = reporting_window(-5)
        self.assertLessEqual(start, end)

    def test_the_cap_keeps_a_typo_from_scanning_the_whole_warehouse(self):
        start, _ = reporting_window(99999)
        self.assertGreaterEqual(start, (date.today() - timedelta(days=730)).isoformat())


class NoSecondImplementationTests(unittest.TestCase):
    """The point of the helper is that nothing computes "today" its own way again."""

    PATHS = ["api/report_schedules.py", "api/kpi_runner.py", "api/nlq_metrics.py",
             "api/snapshot_explorer.py"]

    def test_no_window_builder_uses_a_utc_today(self):
        for rel in self.PATHS:
            src = (ROOT / rel).read_text()
            self.assertNotRegex(
                src, r"datetime\.now\(timezone\.utc\)\.date\(\)",
                f"{rel} computes a UTC 'today'; windows filter business dates",
            )

    def test_report_schedules_uses_the_shared_helper(self):
        src = (ROOT / "api/report_schedules.py").read_text()
        self.assertIn("reporting_today", src)


if __name__ == "__main__":
    unittest.main()
