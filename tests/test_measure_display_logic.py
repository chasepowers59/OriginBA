"""Guardrails for ad hoc measure selection and currency display rules."""

from __future__ import annotations

import unittest


class MeasureDisplayLogicTests(unittest.TestCase):
    """Mirror of apps/analytics-portal measure rules — keep in sync with businessLabels.ts."""

    @staticmethod
    def measure_displays_as_currency(measure_field: str, measure_agg: str) -> bool:
        if measure_field == "*":
            return False
        if measure_agg in {"count", "count_distinct"}:
            return False
        upper = measure_field.upper()
        return "AMT" in upper or "DEBT" in upper or "REVENUE" in upper

    @staticmethod
    def default_measure(trusted: list[str], measures: list[dict]) -> tuple[str, str]:
        preferred = next((m for m in measures if m["id"] in trusted), None)
        if preferred:
            return preferred["id"], preferred["aggs"][0]
        records = next((m for m in measures if m["id"] == "*"), None)
        return "*", (records or {"aggs": ["count"]})["aggs"][0]

    def test_charge_amt_defaults_to_sum(self):
        measures = [
            {"id": "*", "label": "Number of records", "aggs": ["count"]},
            {"id": "CHARGE_AMT", "label": "Charge amount", "aggs": ["sum"]},
        ]
        field, agg = self.default_measure(["CHARGE_AMT"], measures)
        self.assertEqual(field, "CHARGE_AMT")
        self.assertEqual(agg, "sum")

    def test_count_on_charge_amt_is_not_currency(self):
        self.assertFalse(self.measure_displays_as_currency("CHARGE_AMT", "count"))

    def test_sum_on_charge_amt_is_currency(self):
        self.assertTrue(self.measure_displays_as_currency("CHARGE_AMT", "sum"))


if __name__ == "__main__":
    unittest.main()
