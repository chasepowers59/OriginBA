"""A vetted metric with a breakdown answers with the TOTAL, not its largest group.

Ellensburg, 2026-09-29, last 30 days: Ori's zero-cost answer "Customer contacts logged:
1,345" was the largest contact type; the home card counts 3,148. _scalar read the first row
of a grouped query as the headline, so every metric that also shows a breakdown (new
service agreements, customer contacts, collection processes, field activities) reported its
top group. It stayed hidden where the breakdown had one group (field activities by
"Activity Type", one value at Ellensburg), so the first row happened to be the total.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import nlq_metrics  # noqa: E402


class VettedTotalTests(unittest.TestCase):
    def test_a_breakdown_metric_answers_with_the_total(self):
        def run(snapshot_id, spec, date_field, start, end, extra=None, *, organization_id, **_):
            if spec.get("dimensions"):
                return ["Contact Type", "m0"], [["Late notice", 1345], ["General inquiry", 700], ["Door tag", 1103]]
            return ["m0"], [[3148]]
        metric = next(m for m in nlq_metrics.METRICS if m.id == "customer_contacts")
        with mock.patch.object(nlq_metrics, "run_kpi_query", side_effect=run), \
             mock.patch.object(nlq_metrics, "get_snapshot", return_value={"default_date_field": "Contact Date/Time"}), \
             mock.patch.object(nlq_metrics, "allowed_fields", return_value=set()):
            out = nlq_metrics._run_metric(metric, {"days": 30}, organization_id="ellensburg")
        self.assertEqual(out["metrics"]["value"], 3148)
        self.assertTrue(out["narrative"].startswith("Customer contacts logged: 3,148 "))
        self.assertEqual([r["value"] for r in out["table"]["rows"]], [1345, 700, 1103])


class NoTotalTests(unittest.TestCase):
    """Ellensburg 2026-09-29: "Billed usage by unit of measure: 794,109,405" added kWh, gallons and
    therms; "GL dollars by account: $0.00" summed a double-entry ledger, zero by construction, and
    the answer card then warned "No rows in this period". Neither has a total."""

    def _run(self, metric_id, rows):
        metric = next(m for m in nlq_metrics.METRICS if m.id == metric_id)
        with mock.patch.object(nlq_metrics, "run_kpi_query", return_value=(["Group", "m0"], rows)), \
             mock.patch.object(nlq_metrics, "get_snapshot",
                               return_value={"default_date_field": "Accounting Date", "label": "General Ledger"}), \
             mock.patch.object(nlq_metrics, "allowed_fields", return_value=set()):
            return nlq_metrics._run_metric(metric, {"days": 90}, organization_id="ellensburg")

    def test_usage_across_units_and_a_balanced_ledger_have_no_total(self):
        for metric_id, rows in (("billed_usage_by_uom", [["KWH", 700000000], ["GAL", 94000000]]),
                                ("gl_by_account", [["400-471", 19317.0], ["999-999", -19317.0]])):
            out = self._run(metric_id, rows)
            self.assertIsNone(out["metrics"]["value"], metric_id)
            self.assertNotIn("794,", out["narrative"])
            self.assertNotIn("$0.00", out["narrative"])
            self.assertEqual(len(out["table"]["rows"]), 2)

    def test_the_ledger_lists_its_largest_accounts_either_way(self):
        spec = next(m for m in nlq_metrics.METRICS if m.id == "gl_by_account").build({})
        self.assertEqual(spec["query"].get("rank"), "magnitude")

    def test_the_answer_names_its_data_set_by_its_label(self):
        out = self._run("gl_by_account", [["400-471", 1.0]])
        self.assertEqual(out["source_label"], "General Ledger")
        self.assertIn("on General Ledger", out["narrative"])


if __name__ == "__main__":
    unittest.main()
