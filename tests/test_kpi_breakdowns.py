"""A card's breakdown must be able to show more than one bar.

Ellensburg, 2026-09-29: two of the nine home cards said "Nothing to compare: one group".
Payments broke down by Payment Status while its default lens (Frozen) filters on that same
status, so the chart could only ever draw one bar -- the trap the customer-contacts card
already names ("lensing on the trend's own axis would leave a one-bar chart"). Field
activities broke down by Activity Type, which is one value ("Field Activity") on every
Ellensburg row. The breakdowns now are Utility Type (seven groups, Electric $1.62M first)
and Field Task Type (eight: DNP 737, MIMO-R 636, ...), measured on the last 30 days.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402

# Measured one value on every Ellensburg row: a breakdown there is always one bar.
MEASURED_CONSTANT = {("rpt_field_activity", "Activity Type")}


def _concept(field: str) -> str:
    """"Payment Status Code" and "Payment Status" are the same axis, code and label."""
    return field[:-5] if field.endswith(" Code") else field


def _cards():
    workstream = [k for ks in WORKSTREAM_KPIS.values() for k in ks] if isinstance(WORKSTREAM_KPIS, dict) else WORKSTREAM_KPIS
    return [*EXECUTIVE_KPIS, *workstream]


class BreakdownTests(unittest.TestCase):
    def test_no_card_breaks_down_by_the_field_its_lenses_filter_on(self):
        for kpi in _cards():
            dims = {_concept(d) for d in ((kpi.get("trend") or {}).get("dimensions") or [])}
            lensed = {_concept(f["field"]) for lens in kpi.get("lenses") or [] for f in lens.get("filters") or []}
            if kpi.get("lens_field"):
                lensed.add(_concept(kpi["lens_field"]["field"]))
            self.assertFalse(dims & lensed, f"{kpi['id']} breaks down by its own lens field {dims & lensed}")

    def test_no_card_breaks_down_by_a_field_its_filters_pin_to_one_value(self):
        # the Cashiering page's "Payments collected" counts frozen payments only and drew them by status
        for kpi in _cards():
            trend = kpi.get("trend") or {}
            pinned = {_concept(f["field"]) for f in [*(trend.get("filters") or []), *(kpi["value"].get("filters") or [])]
                      if f.get("op") == "eq"}
            dims = {_concept(d) for d in trend.get("dimensions") or []}
            self.assertFalse(dims & pinned, f"{kpi['id']} breaks down by a pinned field {dims & pinned}")

    def test_no_vetted_metric_breaks_down_by_a_column_measured_constant(self):
        from api.nlq_metrics import METRICS
        for m in METRICS:
            for d in (m.build({}).get("query") or {}).get("dimensions") or []:
                self.assertNotIn((m.snapshot_id, d), MEASURED_CONSTANT, m.id)

    def test_net_money_over_transactions_draws_its_credits(self):
        # adjustments net charges against credits and transfers: by adjustment type, ranked by size
        for kpi in _cards():
            trend = kpi.get("trend") or {}
            if kpi["snapshot_id"] == "rpt_financial_txn" and kpi.get("format") == "currency" and trend.get("dimensions"):
                self.assertEqual(trend.get("rank"), "magnitude", kpi["id"])
        adj = next(k for k in WORKSTREAM_KPIS["finance"] if k["id"] == "adjustments")
        self.assertEqual(adj["trend"]["dimensions"], ["Adjustment Type"])

    def test_no_card_breaks_down_by_a_column_measured_constant(self):
        for kpi in _cards():
            for d in (kpi.get("trend") or {}).get("dimensions") or []:
                self.assertNotIn((kpi["snapshot_id"], d), MEASURED_CONSTANT, kpi["id"])


if __name__ == "__main__":
    unittest.main()
