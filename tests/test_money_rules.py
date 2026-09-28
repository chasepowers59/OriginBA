"""Every sum shown over a money canvas carries that canvas's money filters (api/money_rules.py).

Checked everywhere a sum is defined: the home page KPIs, every workstream KPI (card value
and its trend), and every governed metric. Before 2026-09-28 three of them summed
cancelled or unfrozen rows, each found by a different route; one table and one test now.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.money_rules import missing_money_filters  # noqa: E402
from api.nlq_metrics import METRICS  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402


def _kpi_queries(kpi):
    lens = (kpi.get("lenses") or [{}])[0].get("filters")
    for part in ("value", "trend"):
        q = kpi.get(part)
        if isinstance(q, dict):
            yield part, q, lens


class MoneyRuleTests(unittest.TestCase):
    def test_home_page_kpis(self):
        for kpi in EXECUTIVE_KPIS:
            for part, q, lens in _kpi_queries(kpi):
                with self.subTest(kpi=kpi["id"], part=part):
                    self.assertEqual(missing_money_filters(kpi["snapshot_id"], q, lens), [])

    def test_workstream_kpis(self):
        for ws, kpis in WORKSTREAM_KPIS.items():
            for kpi in kpis:
                for part, q, lens in _kpi_queries(kpi):
                    with self.subTest(workstream=ws, kpi=kpi["id"], part=part):
                        self.assertEqual(missing_money_filters(kpi["snapshot_id"], q, lens), [])

    def test_governed_metrics(self):
        for m in METRICS:
            q = m.build({}).get("query", {})
            with self.subTest(metric=m.id):
                self.assertEqual(missing_money_filters(m.snapshot_id, q), [])


if __name__ == "__main__":
    unittest.main()
