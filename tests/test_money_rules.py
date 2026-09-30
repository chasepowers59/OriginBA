"""Every sum shown over a money canvas carries that canvas's money filters (api/money_rules.py).

Checked everywhere a sum is defined: the home page KPIs, every workstream KPI (card value
and its trend), every governed metric and every ready-to-run report in the catalog. Before 2026-09-28 three of them summed
cancelled or unfrozen rows, each found by a different route; one table and one test now.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.money_rules import FROZEN, missing_money_filters  # noqa: E402
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

    def test_ready_to_run_reports(self):
        snapshots = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["snapshots"]
        for sid, snap in snapshots.items():
            for r in snap.get("premade_reports") or []:
                with self.subTest(report=f"{sid}.{r['id']}"):
                    self.assertEqual(missing_money_filters(sid, r), [])


class MeasureRuleTests(unittest.TestCase):
    """Some measures carry their own rule beyond the canvas's. A cancellation FT (AX) carries
    the cancelled adjustment's Adjustment Amount with the SAME sign, so a sum over the canvas
    counts every cancelled adjustment twice (Ellensburg 2026-09-30: $15,572,430.42 shown,
    $15,096,751.09 standing)."""

    def sums(self, field, filters):
        return missing_money_filters("rpt_financial_txn",
                                     {"measures": [{"field": field, "agg": "sum"}], "filters": filters})

    def test_adjustment_amount_needs_standing_adjustments(self):
        for field in ("Adjustment Amount", "Adjustment Base Amount"):
            with self.subTest(field=field):
                self.assertEqual(self.sums(field, [FROZEN]), ["Is Adjustment", "Adjustment Status Code"])

    def test_standing_adjustments_satisfy_it(self):
        standing = [FROZEN, {"field": "Is Adjustment", "op": "eq", "value": True},
                    {"field": "Adjustment Status Code", "op": "eq", "value": "50"}]
        self.assertEqual(self.sums("Adjustment Amount", standing), [])

    def test_a_read_quantity_needs_one_copy_of_each_read(self):
        # one reading rides the segment level, each service point and an audit ('X') copy;
        # tier breakdowns and unit-less derived rows sit beside it (fct_bseg_read's header)
        for field in ("Measured Quantity", "Final Register Quantity"):
            with self.subTest(field=field):
                q = {"measures": [{"field": field, "agg": "sum"}], "filters": [
                    FROZEN, {"field": "Is Cancelled", "op": "eq", "value": False}]}
                self.assertEqual(missing_money_filters("rpt_bill_segment_read", q),
                                 ["Is Segment Level", "Usage Flag", "Read Row Kind"])

    def test_other_measures_on_the_canvas_are_untouched(self):
        self.assertEqual(self.sums("Current Amount", [FROZEN]), [])


# The one sum over every FT type on purpose: its label says it is the net of everything posted.
ALL_TYPES_NET = {"frozen_ft_dollars"}
FT_TYPE_FIELDS = {"Is Bill Segment", "Is Bill Cancellation", "Is Adjustment", "Is Adjustment Cancellation",
                  "Is Payment", "Is Payment Cancellation", "FT Type Code"}


class TransactionTypeTests(unittest.TestCase):
    """A card summing financial transactions says which types. Ellensburg 2026-09-29: Finance's
    "Frozen charge FTs -- Bill segments + adjustments" summed every frozen FT, payments too, and
    showed -$414K for 30 days whose bill segments and adjustments net to $3.24M."""

    def test_every_money_sum_over_transactions_names_its_types(self):
        cards = [*EXECUTIVE_KPIS, *(k for ks in WORKSTREAM_KPIS.values() for k in ks)]
        queries = [(k["id"], k["value"]) for k in cards if k["snapshot_id"] == "rpt_financial_txn"]
        queries += [(m.id, m.build({})["query"]) for m in METRICS
                    if m.snapshot_id == "rpt_financial_txn" and m.id not in ALL_TYPES_NET]
        for kid, q in queries:
            if any(meas.get("agg") == "sum" for meas in q.get("measures") or []):
                with self.subTest(kpi=kid):
                    self.assertTrue({f["field"] for f in q.get("filters") or []} & FT_TYPE_FIELDS)


if __name__ == "__main__":
    unittest.main()
