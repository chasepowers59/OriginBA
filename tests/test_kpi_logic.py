"""KPI cards count what their label says, on the same basis as the cards beside them.

Found 2026-10-01 by scripts/check_kpi_consistency_live.py and a read of the numbers it agreed on:
- "Collection processes" counted rpt_debt_process ROWS, whose grain is process x service
  agreement x event: CityCorp 454,919 rows for 49,425 processes (Ellensburg 375,253 for 37,138);
  and its trend splits collection, severance and write-off, so it is all debt processes.
- "Accounts receivable" summed every SA's Total Balance, so credit balances (deposits held,
  overpayments) netted it down: CityCorp $611,911 beside a "Past-due balance" of $1,253,802,
  because past due sums only balances owed. Receivables are balances owed; both cards now
  stand on that basis.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.nlq_metrics import METRICS  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402

KPI = {k["id"]: k for ks in WORKSTREAM_KPIS.values() for k in ks}
OWED = {"field": "Total Balance", "op": "gte", "value": 0.01}


class KpiLogicTests(unittest.TestCase):
    def test_debt_processes_are_counted_once_each_and_named_for_what_they_are(self):
        kpi = KPI["collection_processes"]   # id kept: saved alerts and lenses refer to it
        for part in ("value", "trend"):
            self.assertEqual(kpi[part]["measures"], [{"field": "Process ID", "agg": "count_distinct"}])
        self.assertEqual(kpi["label"], "Debt processes")   # collection, severance and write-off

    def test_receivables_are_balances_owed_like_past_due(self):
        ar = KPI["accounts_receivable"]["value"]
        self.assertIn({"field": "Total Balance", "op": "gte", "value": 0.01}, ar["filters"])
        self.assertEqual(ar["measures"], KPI["past_due"]["value"]["measures"])


    def test_every_surface_asks_the_same_question(self):
        # the Home card and Ori answer "accounts receivable" and "collection processes" too
        # the Home card chooses with lenses over every balance: Owing first (the default),
        # In credit and Net mean what they say only if the base is unfiltered
        home = {k["id"]: k for k in EXECUTIVE_KPIS}["accounts_receivable"]
        self.assertEqual(home["value"]["filters"], [])
        self.assertEqual(home["lenses"][0]["id"], "owing")
        # split by the SIGN of the Total Balance the card sums, so Owing equals the debt card's
        # receivables: by the Current-Balance credit flag it read $731,460 against $1,254,198
        lenses = {lens["id"]: lens["filters"] for lens in home["lenses"]}
        self.assertEqual(lenses["owing"], [OWED])
        self.assertEqual(lenses["credit"], [{"field": "Total Balance", "op": "lte", "value": -0.01}])
        self.assertEqual(lenses["net"], [])
        ori = {m.id: m.build({})["query"] for m in METRICS}
        self.assertIn(OWED, ori["accounts_receivable"]["filters"])
        self.assertEqual(ori["collection_processes"]["measures"], [{"field": "Process ID", "agg": "count_distinct"}])


if __name__ == "__main__":
    unittest.main()
