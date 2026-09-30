"""A canvas that describes what exists now opens on All dates.

The explorer, Ori's metrics, KPI cards, schedules and the cache warmer applied the canvas's
default window to every question on the canvas's date column. On a canvas of accounts,
agreements, devices or service points that date is when the row was CREATED, so "How many
accounts, by customer class?" counted the accounts set up in the last 12 months: 2,114 of
Ellensburg's 92,832 (2026-09-30); the device estate 2,484 of 55,084; service points 371 of
33,092; and the aged balances, dated by the build, fell outside the frozen anchor entirely.
Such a canvas declares default_date_preset "all_dates": no default window, while the reader
can still choose one.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import cache_warmer as cw  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api.reporting_dates import window_date_field  # noqa: E402

STATE = {"table_name": "rpt_customer_account", "default_date_field": "Account Setup Date",
         "default_date_preset": "all_dates",
         "premade_reports": [{"id": "accounts_by_class", "dimensions": ["Customer Class"],
                              "measures": [{"field": "*", "agg": "count"}], "filters": []}]}
EVENTS = {"table_name": "rpt_bill", "default_date_field": "Bill Date", "default_date_preset": "last_12_months",
          "premade_reports": [{"id": "bills_by_status", "dimensions": ["Bill Status"],
                               "measures": [{"field": "*", "agg": "count"}], "filters": []}]}


class StateCanvases(unittest.TestCase):
    def test_no_default_window_on_a_state_canvas(self):
        self.assertIsNone(window_date_field(STATE))
        self.assertIsNone(se._default_date_filter(STATE))

    def test_an_event_canvas_keeps_its_window(self):
        self.assertEqual(window_date_field(EVENTS), "Bill Date")

    def test_the_warmer_warms_the_state_canvas_unwindowed(self):
        catalog = {"snapshots": {"rpt_customer_account": STATE, "rpt_bill": EVENTS}}
        with mock.patch("api.snapshot_catalog.load_catalog", return_value=catalog), \
             mock.patch.object(se, "_row_estimate", return_value=5_000_000), \
             mock.patch.object(cw, "data_as_of", return_value="2026-06-18"), \
             mock.patch.object(se, "cached_query") as run:
            for _, job in cw._opening_reports("ellensburg"):
                job()
        sent = {call.args[1]["table_name"]: call.args[2].filters for call in run.call_args_list}
        self.assertEqual(sent["rpt_customer_account"], [])
        self.assertEqual([f.field for f in sent["rpt_bill"]], ["Bill Date"])

    def test_a_schedule_on_a_state_canvas_does_not_claim_there_is_no_date(self):
        from api.report_schedules import window_sentence
        self.assertEqual(window_sentence(None, 30, "2026-06-18"), "Data window: all rows, not limited by date.")


if __name__ == "__main__":
    unittest.main()
