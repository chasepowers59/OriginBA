"""Every governed metric that sums money counts only what is money.

The frozen-money rule: only frozen, non-cancelled bill segments are billed money, and
only frozen financial transactions are money at all. The governed "Billed revenue by bill
cycle" summed every segment, so on Ellensburg it put Cycle 5 at $2,699,379.89 for the 90
days to 18 Jun 2026 where frozen money is $2,682,879.14 -- found when the assistant began
answering from the governed metrics first (2026-09-28). The question catalog had the same
flaw fixed the same day; this is its twin in the NLQ metrics.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.nlq_metrics import METRICS  # noqa: E402

BILLED = {"rpt_bill_segment", "rpt_billed_usage"}


def _filters(metric):
    q = metric.build({}).get("query", {})
    return {(f["field"], f["op"], f["value"]) for f in q.get("filters", [])}, q.get("measures", [])


class MoneyFilterTests(unittest.TestCase):
    def test_billed_sums_count_frozen_non_cancelled_segments_only(self):
        for m in METRICS:
            filters, measures = _filters(m)
            if m.snapshot_id in BILLED and any(x.get("agg") == "sum" for x in measures):
                with self.subTest(metric=m.id):
                    self.assertIn(("Is Frozen", "eq", True), filters)
                    self.assertIn(("Is Cancelled", "eq", False), filters)

    def test_financial_transaction_sums_count_frozen_rows_only(self):
        for m in METRICS:
            filters, measures = _filters(m)
            if m.snapshot_id == "rpt_financial_txn" and any(x.get("agg") == "sum" for x in measures):
                with self.subTest(metric=m.id):
                    self.assertIn(("Is Frozen", "eq", True), filters)

    def test_payment_sums_leave_out_cancelled_tenders(self):
        """Payments collected summed every tender: $3,699,296.13 for the 30 days to 18 Jun
        2026 on Ellensburg, where tenders not cancelled come to $3,660,439.03 -- the
        home page's figure."""
        for m in METRICS:
            filters, measures = _filters(m)
            if m.snapshot_id == "rpt_payment_tender" and any(x.get("agg") == "sum" for x in measures):
                with self.subTest(metric=m.id):
                    self.assertIn(("Is Cancelled", "eq", False), filters)


if __name__ == "__main__":
    unittest.main()
