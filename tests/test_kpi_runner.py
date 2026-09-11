"""KPI windows, trends and the date field a card measures on.

`execute_kpi_definition` (7 uses), `date_windows` (4), `run_kpi_query` (3) and
`trend_from_rows` (3) were named in no test, while being what every number on the home
page is computed from.

`date_windows` turns out to be correct, including the two edges worth doubting — the
Feb-29 year subtraction and month-to-date on the 1st — so most of this pins behaviour
rather than changing it. That is the point: these are the comparisons an executive
reads, and "vs prior 30d" being off by a day is not visible on the card.

The one change: `execute_kpi_definition` resolved its date field with its own
`required_date_field or default_date_field` chain — the fourth copy of a rule that
already caused a real bug in three other places (see api/reporting_dates.py). It now
calls `window_date_field` for that half and keeps the KPI's own override in front.
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kpi_runner import date_windows, pct_change, trend_from_rows  # noqa: E402


def span(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


class DateWindowsTests(unittest.TestCase):
    def test_prior_period_compares_equal_spans(self):
        (cs, ce), (ps, pe), label = date_windows(30)
        self.assertEqual(ce, date.today().isoformat())
        self.assertEqual(span(cs, ce), 30)
        self.assertEqual(span(ps, pe), 30, "the comparison is meaningless on unequal spans")
        self.assertEqual(label, "vs prior 30d")

    def test_the_prior_window_ends_the_day_before_the_current_one_starts(self):
        (cs, _), (_, pe), _ = date_windows(30)
        self.assertEqual(date.fromisoformat(pe), date.fromisoformat(cs) - timedelta(days=1),
                         "an overlapping or gapped comparison double-counts a day")

    def test_a_nonsense_span_is_clamped_rather_than_inverted(self):
        for days in (0, -5):
            (cs, ce), _, _ = date_windows(days)
            self.assertLessEqual(cs, ce)

    def test_the_cap_keeps_a_card_from_scanning_everything(self):
        (cs, ce), _, _ = date_windows(99999)
        self.assertLessEqual(span(cs, ce), 365)

    def test_yoy_moves_both_ends_back_a_year(self):
        (cs, ce), (ps, pe), label = date_windows(30, "yoy")
        self.assertEqual(label, f"vs {date.today().year - 1}")
        self.assertEqual(span(ps, pe), span(cs, ce),
                         "a seasonal comparison must cover the same number of days")

    def test_yoy_survives_february_29(self):
        """`.replace(year=...)` raises on Feb 29; the fallback subtracts 365 instead."""
        import api.kpi_runner as kr
        with mock.patch.object(kr, "date", wraps=date) as fake:
            fake.today.return_value = date(2028, 2, 29)  # a leap day
            (cs, ce), (ps, pe), _ = date_windows(30, "yoy")
        self.assertEqual(ce, "2028-02-29")
        self.assertEqual(span(ps, pe), span(cs, ce))

    def test_mom_runs_month_to_date_against_the_same_span_last_month(self):
        import api.kpi_runner as kr
        with mock.patch.object(kr, "date", wraps=date) as fake:
            fake.today.return_value = date(2026, 7, 10)
            (cs, ce), (ps, pe), label = date_windows(30, "mom")
        self.assertEqual((cs, ce), ("2026-07-01", "2026-07-10"))
        self.assertEqual((ps, pe), ("2026-06-01", "2026-06-10"))
        self.assertEqual(label, "vs June", "the label must name the month being compared")

    def test_mom_on_the_first_of_the_month_does_not_invert(self):
        import api.kpi_runner as kr
        with mock.patch.object(kr, "date", wraps=date) as fake:
            fake.today.return_value = date(2026, 7, 1)
            (cs, ce), (ps, pe), _ = date_windows(30, "mom")
        self.assertLessEqual(cs, ce)
        self.assertLessEqual(ps, pe)

    def test_mom_clamps_to_a_shorter_previous_month(self):
        """31 March compared to February must not run off the end of February."""
        import api.kpi_runner as kr
        with mock.patch.object(kr, "date", wraps=date) as fake:
            fake.today.return_value = date(2026, 3, 31)
            _, (ps, pe), _ = date_windows(30, "mom")
        self.assertEqual(ps, "2026-02-01")
        self.assertLessEqual(pe, "2026-02-28")

    def test_every_boundary_is_a_plain_date(self):
        for mode in ("prior_period", "mom", "yoy"):
            (cs, ce), (ps, pe), _ = date_windows(30, mode)
            for value in (cs, ce, ps, pe):
                self.assertRegex(value, r"^\d{4}-\d{2}-\d{2}$", mode)


class TrendFromRowsTests(unittest.TestCase):
    def test_maps_first_column_to_label_and_last_to_value(self):
        self.assertEqual(
            trend_from_rows(["month", "total"], [["2026-01", 5], ["2026-02", 7.5]]),
            [{"label": "2026-01", "value": 5.0}, {"label": "2026-02", "value": 7.5}])

    def test_a_null_label_reads_as_Unknown_rather_than_None(self):
        self.assertEqual(trend_from_rows(["m", "t"], [[None, 3]])[0]["label"], "Unknown")

    def test_a_null_value_is_zero_on_a_bar_chart(self):
        self.assertEqual(trend_from_rows(["m", "t"], [["x", None]])[0]["value"], 0.0)

    def test_one_column_cannot_form_a_trend(self):
        self.assertEqual(trend_from_rows(["only"], [["x"]]), [])

    def test_no_rows_is_an_empty_trend_not_an_error(self):
        self.assertEqual(trend_from_rows(["m", "t"], []), [])


class PctChangeTests(unittest.TestCase):
    def test_ordinary_growth_and_decline(self):
        self.assertAlmostEqual(pct_change(110, 100), 10.0)
        self.assertAlmostEqual(pct_change(90, 100), -10.0)

    def test_a_zero_prior_has_no_percentage(self):
        """Not infinity, and not 100%: there is no meaningful change from nothing."""
        self.assertIsNone(pct_change(50, 0))

    def test_a_missing_side_has_no_percentage(self):
        self.assertIsNone(pct_change(None, 100))
        self.assertIsNone(pct_change(100, None))

    def test_a_negative_prior_keeps_the_direction_readable(self):
        """abs(prior) in the denominator: moving from -100 to -50 is an INCREASE."""
        self.assertAlmostEqual(pct_change(-50, -100), 50.0)


class KpiDateFieldTests(unittest.TestCase):
    """The card's own override wins; otherwise the one shared rule decides."""

    def test_execute_uses_the_shared_window_date_field(self):
        from api.reporting_dates import window_date_field
        self.assertEqual(window_date_field({"default_date_field": "Bill Date"}), "Bill Date")
        self.assertIsNone(window_date_field({}))

    def test_kpi_runner_no_longer_carries_its_own_copy(self):
        import re
        src = (ROOT / "api" / "kpi_runner.py").read_text()
        # assertNotRegex prints the whole HAYSTACK on failure, which for a module is
        # unreadable; compare a boolean so the message is the message.
        duplicated = bool(re.search(
            r'snapshot\.get\("required_date_field"\)\s*\n?\s*or snapshot\.get\("default_date_field"\)',
            src))
        self.assertFalse(duplicated,
                         "kpi_runner re-implements window_date_field; that chain caused a real bug")
        self.assertIn("window_date_field", src)


if __name__ == "__main__":
    unittest.main()
