"""Tests for the drag-and-drop builder's query assembly and multi-measure path.

The builder targets the existing governed build_query with ARRAYS of dimensions and
measures. These lock in: multi-dimension + multi-measure SQL, the oracle_dbt dialect
(quoted Title-Case identifiers, Oracle binds), sum gated by trusted_measures, and the
aggregation allow-list.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.query_builder import QueryValidationError, build_query  # noqa: E402

FIELDS = {"FT Type", "CIS Division", "Current Amount", "Total Amount (Payoff)", "Accounting Date"}
TRUSTED = {"Current Amount", "Total Amount (Payoff)"}


def _build(dialect, schema, **kw):
    return build_query(
        table_name="rpt_financial_txn",
        allowed_fields=FIELDS,
        trusted_measures=TRUSTED,
        required_date_field=None,
        dimensions=kw.get("dimensions", []),
        measures=kw.get("measures", [{"field": "*", "agg": "count"}]),
        filters=kw.get("filters", []),
        limit=kw.get("limit", 100),
        time_dimensions=kw.get("time_dimensions"),
        dialect=dialect,
        schema=schema,
    )


class MultiMeasureBuilderTests(unittest.TestCase):
    def test_multi_dimension_multi_measure_postgres(self):
        sql, binds = _build(
            "postgres", "reporting",
            dimensions=["FT Type", "CIS Division"],
            measures=[{"field": "*", "agg": "count"}, {"field": "Current Amount", "agg": "sum"}],
        )
        self.assertIn('"FT Type"', sql)
        self.assertIn('"CIS Division"', sql)
        self.assertIn('COUNT(*) AS "m0"', sql)
        self.assertIn('SUM("Current Amount") AS "m1"', sql)
        self.assertIn("GROUP BY", sql)
        self.assertIn('reporting."rpt_financial_txn"', sql)

    def test_oracle_dbt_dialect_titlecase_and_binds(self):
        sql, binds = _build(
            "oracle_dbt", "ORIGINBA_REPORTING",
            dimensions=["FT Type"],
            measures=[{"field": "Current Amount", "agg": "sum"}],
            filters=[{"field": "FT Type", "op": "eq", "value": "BS"}],
        )
        self.assertIn('"FT Type"', sql)              # quoted Title-Case, like postgres
        self.assertIn('SUM("Current Amount")', sql)
        self.assertIn(":b0", sql)                    # Oracle bind, not %(b0)s
        self.assertNotIn("%(", sql)
        self.assertIn("ORIGINBA_REPORTING.RPT_FINANCIAL_TXN", sql)  # unquoted -> Oracle upper
        self.assertEqual(binds["b0"], "BS")

    def test_sum_blocked_on_untrusted_measure(self):
        with self.assertRaises(QueryValidationError):
            _build("postgres", "reporting",
                   measures=[{"field": "Accounting Date", "agg": "sum"}])

    def test_invalid_aggregation_rejected(self):
        with self.assertRaises(QueryValidationError):
            _build("postgres", "reporting",
                   measures=[{"field": "Current Amount", "agg": "median"}])

    def test_unknown_field_rejected(self):
        with self.assertRaises(QueryValidationError):
            _build("postgres", "reporting", dimensions=["Nonexistent Column"])

    def test_time_dimension_bucketing(self):
        sql, _ = _build(
            "oracle_dbt", "ORIGINBA_REPORTING",
            time_dimensions=[{"field": "Accounting Date", "grain": "month"}],
            measures=[{"field": "*", "agg": "count"}],
        )
        self.assertIn("TRUNC(", sql)
        self.assertIn("TD0", sql)


if __name__ == "__main__":
    unittest.main()
