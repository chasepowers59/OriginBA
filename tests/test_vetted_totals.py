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


if __name__ == "__main__":
    unittest.main()
