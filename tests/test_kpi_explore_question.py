"""A KPI card opens the question that produced its number.

All 44 Home and workstream cards linked to their data set's bare page, which opens on "Choose a
standard report" (2026-10-01): a reader could not see where a card's number came from. Each card
now carries the exact question it asked (measures, its filters, the lens, the window) so the
builder can open it and show the same number."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import kpi_runner as kr  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402

KPI = {k["id"]: k for ks in WORKSTREAM_KPIS.values() for k in ks}


class ExploreQuestionTests(unittest.TestCase):
    def _card(self, kpi_id, extra=None):
        with mock.patch.object(kr, "run_kpi_query", return_value=(["m0"], [[42]])), \
             mock.patch.object(kr, "date_windows", return_value=(("2025-07-17", "2026-07-17"), ("2024-07-16", "2025-07-16"), None)):
            return kr.execute_kpi_definition(KPI[kpi_id], days=365, extra_filters=extra, organization_id="dev")

    def test_a_windowed_card_carries_its_measure_filters_and_window(self):
        card = self._card("billed_amount", extra=[{"field": "Service Type", "op": "in", "value": ["Water"]}])
        q = card["explore_question"]
        self.assertEqual(q["snapshot_id"], "rpt_bill_segment")
        self.assertEqual(q["measures"], KPI["billed_amount"]["value"]["measures"])
        self.assertEqual(q["dimensions"], [])
        for f in KPI["billed_amount"]["value"]["filters"]:
            self.assertIn(f, q["filters"])
        self.assertIn({"field": "Service Type", "op": "in", "value": ["Water"]}, q["filters"])
        self.assertIn({"field": "Bill Date", "op": "between", "value": ["2025-07-17", "2026-07-17"]}, q["filters"])

    def test_a_windowless_card_has_no_window(self):
        q = self._card("accounts_receivable")["explore_question"]
        self.assertFalse(any(f["op"] == "between" for f in q["filters"]))
        self.assertTrue(q["all_dates"])


if __name__ == "__main__":
    unittest.main()
