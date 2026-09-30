"""Averages and shares in the governed query builder.

Fifteen ready-to-run reports promised a rate or an average ("Estimation rate", "Avg Days To
Pay", "First-time fix %") and charted a row count under that title, because the builder
could only count, sum, and take a min or max (2026-09-30). Two aggregations close that:
`avg` over a trusted numeric measure, and `share` -- the percentage of rows where a boolean
field is true, every row in the denominator (a blank flag is not true). Neither adds up
across groups, and neither is answered by a pre-aggregate.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.aggregate_routing import _rewrite  # noqa: E402
from api.query_builder import QueryValidationError, build_query  # noqa: E402

FIELDS = {"Bill Cycle", "Billed Amount", "Estimated Segment", "Days To Pay"}
TRUSTED = {"Billed Amount", "Days To Pay"}
BOOLEANS = {"Estimated Segment"}


def build(dialect, measures, **kw):
    return build_query(
        table_name="rpt_bill_segment", allowed_fields=FIELDS, trusted_measures=TRUSTED,
        boolean_fields=kw.get("booleans", BOOLEANS), dimensions=["Bill Cycle"], measures=measures,
        filters=[], limit=100, dialect=dialect,
        schema="reporting" if dialect == "postgres" else "ORIGINBA_REPORTING",
    )[0]


class Average(unittest.TestCase):
    def test_avg_of_a_trusted_measure(self):
        for dialect in ("postgres", "oracle_dbt"):
            with self.subTest(dialect=dialect):
                self.assertIn('AVG("Days To Pay") AS "m0"', build(dialect, [{"field": "Days To Pay", "agg": "avg"}]))

    def test_avg_is_held_to_the_sum_rule(self):
        with self.assertRaises(QueryValidationError):
            build("postgres", [{"field": "Bill Cycle", "agg": "avg"}])
        with self.assertRaises(QueryValidationError):
            build("postgres", [{"field": "*", "agg": "avg"}])


class Share(unittest.TestCase):
    def test_share_is_the_percentage_of_all_rows_where_the_flag_is_true(self):
        self.assertIn('100.0 * AVG(CASE WHEN "Estimated Segment" THEN 1 ELSE 0 END) AS "m0"',
                      build("postgres", [{"field": "Estimated Segment", "agg": "share"}]))
        # Oracle stores flags as BOOLEAN (23ai canvases) or NUMBER 1/0 (aggregates, 19c): = 1 reads both
        self.assertIn('100.0 * AVG(CASE WHEN "Estimated Segment" = 1 THEN 1 ELSE 0 END) AS "m0"',
                      build("oracle_dbt", [{"field": "Estimated Segment", "agg": "share"}]))

    def test_share_needs_a_boolean_field(self):
        for field in ("Billed Amount", "Bill Cycle", "*"):
            with self.subTest(field=field), self.assertRaises(QueryValidationError):
                build("postgres", [{"field": field, "agg": "share"}])

    def test_share_is_refused_when_the_caller_names_no_booleans(self):
        with self.assertRaises(QueryValidationError):
            build("postgres", [{"field": "Estimated Segment", "agg": "share"}], booleans=set())


class NeitherIsPreAggregated(unittest.TestCase):
    def test_routing_refuses_avg_and_share(self):
        agg = {"table": "agg_x_daily", "date": "Bill Date", "dimensions": ["Bill Cycle", "Estimated Segment"],
               "measures": {"Billed Amount": "sum"}, "count": "Record Count", "build_column": "Canvas Build"}
        for m in ({"field": "Billed Amount", "agg": "avg"}, {"field": "Estimated Segment", "agg": "share"}):
            with self.subTest(m=m):
                self.assertIsNone(_rewrite(agg, [], ["Bill Cycle"], [m], []))


if __name__ == "__main__":
    unittest.main()


class EveryCallerNamesItsBooleans(unittest.TestCase):
    """A caller that runs a report's or a reader's measures and forgets boolean_fields refuses
    every share: the explorer, Ori's saved views, embeds, KPI cards and schedules all pass it."""

    def test_the_callers(self):
        import re
        for path in ("api/snapshot_explorer.py", "api/assistant.py", "api/embed.py", "api/kpi_runner.py",
                     "api/report_schedules.py"):
            src = (ROOT / path).read_text()
            calls = [c for c in re.findall(r"build_query\((.*?)\)\n", src, re.S)
                     if 'measures=[{"field": "*", "agg": "count"}]' not in c]  # row counts only
            with self.subTest(path=path):
                self.assertTrue(calls, path)
                self.assertTrue(all("boolean_fields=boolean_fields(" in c for c in calls), path)

    def test_boolean_fields_reads_the_catalog_types(self):
        from api.snapshot_catalog import boolean_fields
        snap = {"fields": [{"id": "Estimated Segment", "type": "boolean"}, {"id": "Billed Amount", "type": "numeric"}]}
        self.assertEqual(boolean_fields(snap), {"Estimated Segment"})


class Labels(unittest.TestCase):
    def test_the_result_names_the_aggregation(self):
        from api.snapshot_explorer import _result_labels
        snap = {"fields": [{"id": "Days To Pay", "label": "Days To Pay"}, {"id": "Estimated Segment", "label": "Estimated Segment"}]}
        got = _result_labels(snap, ["m0", "m1"], [], [{"field": "Days To Pay", "agg": "avg"},
                                                      {"field": "Estimated Segment", "agg": "share"}], [])
        self.assertEqual(got, {"m0": "Average Days To Pay", "m1": "% Estimated Segment"})
