"""A zero should say whether it means "none happened" or "none in this window".

Three cards in a row read 0 for the same reason and none of them said so: bills windowed
on an empty column, field activities on a 17%-populated one, and billed revenue looked
wrong until the window turned out to end today while the data ran to 2029. In each case
the number was correct and useless, because "0" carries no way to tell a genuine zero
from a window that missed the data.

So a windowed KPI that comes back empty reports the latest date its canvas actually
holds, and the card says "no data in this window — latest 25 Mar 2022". A KPI with a
real non-zero value never pays for the extra lookup, and a stock metric has no window to
be wrong about.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import kpi_runner  # noqa: E402


class EmptyWindowTests(unittest.TestCase):
    def test_reports_the_latest_date_when_the_window_is_empty(self) -> None:
        with mock.patch.object(kpi_runner, "_latest_date", return_value="2022-03-25"):
            self.assertEqual(
                kpi_runner.empty_window_note(
                    value=0, windowless=False, snapshot_id="rpt_field_activity",
                    date_field="Created Date/Time", organization_id="dev",
                ),
                {"latest": "2022-03-25"},
            )

    def test_a_null_value_counts_as_empty(self) -> None:
        with mock.patch.object(kpi_runner, "_latest_date", return_value="2022-03-25"):
            self.assertIsNotNone(kpi_runner.empty_window_note(
                value=None, windowless=False, snapshot_id="s",
                date_field="d", organization_id="dev"))

    def test_a_real_value_never_pays_for_the_lookup(self) -> None:
        with mock.patch.object(kpi_runner, "_latest_date") as latest:
            self.assertIsNone(kpi_runner.empty_window_note(
                value=104, windowless=False, snapshot_id="s",
                date_field="d", organization_id="dev"))
            latest.assert_not_called()

    def test_a_stock_metric_has_no_window_to_be_wrong_about(self) -> None:
        with mock.patch.object(kpi_runner, "_latest_date") as latest:
            self.assertIsNone(kpi_runner.empty_window_note(
                value=0, windowless=True, snapshot_id="s",
                date_field=None, organization_id="dev"))
            latest.assert_not_called()

    def test_a_canvas_with_no_rows_at_all_gets_no_note(self) -> None:
        """Then the zero IS the whole truth and needs no excuse."""
        with mock.patch.object(kpi_runner, "_latest_date", return_value=None):
            self.assertIsNone(kpi_runner.empty_window_note(
                value=0, windowless=False, snapshot_id="s",
                date_field="d", organization_id="dev"))

    def test_a_failed_lookup_is_silent_rather_than_fatal(self) -> None:
        with mock.patch.object(kpi_runner, "_latest_date", side_effect=RuntimeError("db")):
            self.assertIsNone(kpi_runner.empty_window_note(
                value=0, windowless=False, snapshot_id="s",
                date_field="d", organization_id="dev"))


if __name__ == "__main__":
    unittest.main()
