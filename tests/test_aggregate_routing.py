"""A report is answered from a pre-aggregate only when the answer is provably the canvas's.

api/aggregate_routing.py implements the six rules of the pre-aggregates plan
(originba_dbt docs/PRE_AGGREGATES_PLAN.md) and refuses by default: anything it does not
recognise goes to the canvas, so a new query-builder feature never routes by accident.
Each test here names one way an aggregate would give a different number, and proves the
router sends that query to the canvas instead. The numbers themselves are compared
routed vs unrouted in tests/test_aggregate_parity.py.

The catalog block comes from a copy of catalog_dbt.json with the block added by hand
(tests/fixtures/catalog_dbt_aggregate.json): output/catalog_dbt.json gets it when
originba_dbt's scripts/build_portal_catalog.py next regenerates it.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import aggregate_routing as ar  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache as sc  # noqa: E402
from api.query_builder import build_query  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "catalog_dbt_aggregate.json").read_text())
CANVAS = FIXTURE["snapshots"]["rpt_billed_charge"]
AGG = "agg_billed_charge_daily"
BUILD = "74227:74227"

WINDOW = {"field": "Bill Date", "op": "between", "value": ["2025-09-29", "2026-09-29"]}
SUM_BILLED = {"field": "Billed Amount", "agg": "sum"}
COUNT = {"field": "*", "agg": "count"}


def plan(filters=(), dimensions=("Customer Class",), measures=(SUM_BILLED,), time_dimensions=(),
         snapshot=CANVAS):
    return ar.plan(snapshot, list(filters), list(dimensions), list(measures), list(time_dimensions), "org")


class RoutingRules(unittest.TestCase):
    def setUp(self):
        # rule 6 reads the database; here the aggregate and the canvas agree unless a test says not
        self.identity = mock.patch.object(ar, "_builds", return_value=[(BUILD, BUILD)])
        self.builds = self.identity.start()

    def tearDown(self):
        self.identity.stop()

    def test_the_opening_report_with_a_row_rule_routes(self):
        rule = {"field": "Service Type", "op": "in", "value": ["Water"]}
        self.assertEqual(plan([WINDOW, rule]), (AGG, [SUM_BILLED]))

    def test_a_count_becomes_the_sum_of_the_stored_counts(self):
        table, measures = plan([WINDOW], measures=[COUNT, SUM_BILLED])
        self.assertEqual([(m["field"], m["agg"]) for m in measures],
                         [("Record Count", "sum"), ("Billed Amount", "sum")])

    def test_all_time_and_gte_and_date_buckets_route(self):
        self.assertIsNotNone(plan([]))
        self.assertIsNotNone(plan([{"field": "Bill Date", "op": "gte", "value": "2026-01-01"}]))
        for grain in ("month", "quarter", "year"):
            self.assertIsNotNone(plan([WINDOW], dimensions=[],
                                      time_dimensions=[{"field": "Bill Date", "grain": grain}]))

    # rule 1
    def test_a_catalog_without_an_aggregate_is_refused(self):
        bare = {k: v for k, v in CANVAS.items() if k != "aggregate"}
        self.assertIsNone(plan([WINDOW], snapshot=bare))

    # rule 2
    def test_a_dimension_the_aggregate_does_not_carry_is_refused(self):
        self.assertIsNone(plan([WINDOW], dimensions=["Customer Class", "City"]))

    def test_the_date_as_a_plain_dimension_is_refused(self):
        # the aggregate holds the DAY; the canvas groups by the full timestamp
        self.assertIsNone(plan([WINDOW], dimensions=["Bill Date"]))

    def test_a_filter_on_a_field_the_aggregate_does_not_carry_is_refused(self):
        self.assertIsNone(plan([WINDOW, {"field": "City", "op": "eq", "value": "Ellensburg"}]))
        self.assertIsNone(plan([{"field": "Due Date", "op": "between", "value": ["2026-01-01", "2026-02-01"]}]))

    def test_a_row_rule_on_a_column_the_aggregate_does_not_carry_is_refused(self):
        self.assertIsNone(plan([WINDOW, {"field": "Premise Type", "op": "in", "value": ["Residential"]}]))

    def test_the_aggregates_own_columns_are_not_canvas_fields(self):
        self.assertIsNone(plan([WINDOW], dimensions=["Canvas Build"]))
        self.assertIsNone(plan([WINDOW, {"field": "Record Count", "op": "gte", "value": 2}]))

    def test_a_filter_shape_it_does_not_know_is_refused(self):
        self.assertIsNone(plan([WINDOW, {"field": "Customer Class", "op": "like", "value": "Res%"}]))
        self.assertIsNone(plan([{**WINDOW, "negate": True}]))

    # rule 3
    def test_lte_eq_neq_and_in_on_the_date_are_refused(self):
        # on the canvas `<= d` means midnight of d; the aggregate's day d holds the whole day
        for op, value in (("lte", "2026-01-01"), ("eq", "2026-01-01"), ("neq", "2026-01-01"),
                          ("in", ["2026-01-01"])):
            with self.subTest(op=op):
                self.assertIsNone(plan([{"field": "Bill Date", "op": op, "value": value}]))

    def test_a_date_window_that_is_not_plain_dates_is_refused(self):
        for value in (["2026-01-01T12:00:00", "2026-02-01"], ["2026-01-01", None], "2026-01-01",
                      ["2026-13-01", "2026-02-01"]):
            with self.subTest(value=value):
                self.assertIsNone(plan([{"field": "Bill Date", "op": "between", "value": value}]))
        self.assertIsNone(plan([{"field": "Bill Date", "op": "gte", "value": "2026-01-01 06:00"}]))

    # rule 4
    def test_a_time_bucket_on_another_field_is_refused(self):
        self.assertIsNone(plan([WINDOW], dimensions=[],
                               time_dimensions=[{"field": "Due Date", "grain": "month"}]))

    def test_a_bucket_finer_or_other_than_month_quarter_year_is_refused(self):
        self.assertIsNone(plan([WINDOW], dimensions=[],
                               time_dimensions=[{"field": "Bill Date", "grain": "day"}]))

    # rule 5
    def test_measures_off_the_allowlist_are_refused(self):
        for measure in ({"field": "Account ID", "agg": "count_distinct"},
                        {"field": "Billed Amount", "agg": "avg"},
                        {"field": "Billed Amount", "agg": "min"},
                        {"field": "Billed Amount", "agg": "max"},
                        {"field": "Billed Amount", "agg": "count"},
                        {"field": "Base Amount", "agg": "sum"}):
            with self.subTest(measure=measure):
                self.assertIsNone(plan([WINDOW], measures=[SUM_BILLED, measure]))

    # rule 6
    def test_an_aggregate_from_another_canvas_build_is_refused(self):
        self.builds.return_value = [("74227:74227", "74440:74440")]
        self.assertIsNone(plan([WINDOW]))

    def test_an_aggregate_that_is_not_one_build_is_refused(self):
        for rows in ([], [(None, BUILD)], [(BUILD, BUILD), ("1:1", BUILD)], [(BUILD, None)]):
            with self.subTest(rows=rows):
                self.builds.return_value = rows
                self.assertIsNone(plan([WINDOW]))

    def test_any_error_reading_the_identity_is_refused(self):
        self.builds.side_effect = RuntimeError("relation does not exist")
        self.assertIsNone(plan([WINDOW]))

    def test_the_identity_is_not_read_when_a_static_rule_already_refused(self):
        plan([WINDOW], dimensions=["City"])
        self.builds.assert_not_called()


class IdentityQuery(unittest.TestCase):
    def test_postgres_and_oracle_read_the_same_identity_dbt_recorded(self):
        for backend, dialect, schema, needle in (
                ("postgres", "postgres", "reporting", "relfilenode"),
                ("oracle", "oracle_dbt", "ORIGINBA_REPORTING", "all_objects")):
            with self.subTest(backend=backend), \
                    mock.patch.object(ar, "snapshot_backend", return_value=(backend, dialect, schema)), \
                    mock.patch("api.warehouse_db.execute_query", return_value=(["a", "b"], [[BUILD, BUILD]])) as pg, \
                    mock.patch("api.demo_db.execute_query", return_value=(["a", "b"], [[BUILD, BUILD]])) as ora:
                self.assertEqual(ar._builds(CANVAS, CANVAS["aggregate"], "org"), [(BUILD, BUILD)])
                ran = (pg if backend == "postgres" else ora).call_args
                self.assertIn(needle, ran.args[0])
                self.assertIn('"Canvas Build"', ran.args[0])


class CatalogCopy(unittest.TestCase):
    """The fixture is a copy; it must not drift from the catalog the portal serves."""

    def test_the_copy_matches_the_real_catalog_where_routing_reads_it(self):
        real = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["snapshots"]["rpt_billed_charge"]
        for key in ("table_name", "default_date_field", "default_date_preset", "premade_reports", "trusted_measures"):
            self.assertEqual(CANVAS[key], real[key], key)
        self.assertEqual([f["id"] for f in CANVAS["fields"]], [f["id"] for f in real["fields"]])
        if "aggregate" in real:
            self.assertEqual(CANVAS["aggregate"], real["aggregate"])


class CachedQueryHook(unittest.TestCase):
    """cached_query asks the router on a cache miss and runs the aggregate statement it builds."""

    def setUp(self):
        sc.clear()
        self.ran: list[str] = []

        def execute(sql, binds=None, **_):
            self.ran.append(sql)
            if "SELECT DISTINCT" in sql:
                return ["b", "live"], [list(self.identity)]
            return ["Customer Class", "m0"], [["Residential", 5]]

        self.identity = (BUILD, BUILD)
        self.patches = [
            mock.patch.object(se, "snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch.object(ar, "snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch.object(se, "data_version", return_value="v1"),
            mock.patch("api.warehouse_db.execute_query", side_effect=execute),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        sc.clear()

    def query(self, measures=(COUNT,)):
        body = se.QueryRequest(dimensions=["Customer Class"], measures=list(measures), filters=[WINDOW])
        return se.cached_query("org", CANVAS, body, [WINDOW])

    def test_a_routed_query_reads_the_aggregate_and_says_so(self):
        sql, columns, rows, served_from = self.query()
        self.assertEqual(served_from, AGG)
        self.assertIn(f'FROM reporting."{AGG}"', sql)
        self.assertIn('COALESCE(SUM("Record Count"), 0) AS "m0"', sql)
        self.assertEqual(self.ran[-1], sql)

    def test_a_stored_sum_is_summed(self):
        sql, *_ = self.query(measures=[SUM_BILLED])
        self.assertIn('SUM("Billed Amount") AS "m0"', sql)
        self.assertNotIn("COALESCE", sql)

    def test_an_identity_mismatch_reads_the_canvas(self):
        self.identity = ("74227:74227", "74440:74440")
        sql, _, _, served_from = self.query()
        self.assertEqual(served_from, "rpt_billed_charge")
        self.assertIn('FROM reporting."rpt_billed_charge"', sql)
        self.assertIn('COUNT(*) AS "m0"', sql)

    def test_the_identity_is_read_once_per_cache_miss(self):
        self.query()
        self.query()
        self.assertEqual(sum("SELECT DISTINCT" in s for s in self.ran), 1)

    def test_an_unroutable_query_reads_the_canvas_without_asking_the_database(self):
        body = se.QueryRequest(dimensions=["City"], measures=[COUNT], filters=[WINDOW])
        sql, _, _, served_from = se.cached_query("org", CANVAS, body, [WINDOW])
        self.assertEqual(served_from, "rpt_billed_charge")
        self.assertFalse(any("SELECT DISTINCT" in s for s in self.ran))


class OrderTieBreak(unittest.TestCase):
    """The row limit keeps the top N by the first measure; ties must fall the same way on the
    canvas and on its aggregate, so the rest of the grouping decides them."""

    def sql(self, time_dimensions=None):
        sql, _ = build_query(table_name="rpt_billed_charge", allowed_fields={"Bill Date", "Customer Class", "Budget Plan", "Billed Amount"},
                             trusted_measures={"Billed Amount"}, dimensions=["Customer Class", "Budget Plan"],
                             measures=[SUM_BILLED], filters=[], limit=6, time_dimensions=time_dimensions,
                             dialect="postgres", schema="reporting")
        return sql

    def test_ties_on_the_measure_are_broken_by_the_groups(self):
        self.assertIn('ORDER BY "m0" DESC NULLS LAST, "Customer Class", "Budget Plan" FETCH', self.sql())

    def test_ties_on_the_time_bucket_are_broken_by_the_groups(self):
        self.assertIn('ORDER BY "TD0" DESC NULLS LAST, "Customer Class", "Budget Plan" FETCH',
                      self.sql([{"field": "Bill Date", "grain": "month"}]))


if __name__ == "__main__":
    unittest.main()
