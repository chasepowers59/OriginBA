"""Routed == unrouted, exactly, on a real warehouse built by dbt.

For every aggregated canvas: every ready-to-run report, every home and workstream card and
governed question on that canvas (with each question parameter the canvas carries), a count
by Service Type, a month trend and the money-rule total, over every named window (as of the
data's last date), the 180-day fallback and all time, with no row rule and with Service Type
rules, twice through cached_query: once with the catalog's aggregate block (routed to the
canvas's daily aggregate) and once without it (the canvas). The rows must be identical, in
the same order, and the routed run must really have been served by the aggregate. The
opening report -- the first ready-to-run report in the window the server applies when the
reader sets none -- must route too.

Needs the disposable fixture warehouse from originba_dbt (`dbt build --target local`,
port 5433) with the aggregates built. Reads the connection from the variables the dbt
`local` target and scripts/lib/local-env.sh read (DBT_HOST, DBT_PORT, DBT_USER,
DBT_PASSWORD, DBT_DBNAME), with the same defaults; skips when that database is not
there. Never runs against 5432, which holds real client data.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import aggregate_routing as ar  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache as sc  # noqa: E402
from api.date_presets import NAMED, preset_range  # noqa: E402
from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.money_rules import MONEY_FILTERS  # noqa: E402
from api.nlq_metrics import _PARAM_FIELDS, METRICS  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402

SNAPSHOTS = json.loads((ROOT / "tests" / "fixtures" / "catalog_dbt_aggregate.json").read_text())["snapshots"]
CANVASES = ["rpt_billed_charge", "rpt_gl", "rpt_financial_txn", "rpt_billed_usage"]
BACKEND = ("postgres", "postgres", "reporting")
COUNT = {"field": "*", "agg": "count"}


def _connect():
    port = os.environ.get("DBT_PORT") or "5433"
    if port == "5432":
        raise unittest.SkipTest("DBT_PORT=5432 is the real-data Postgres; parity runs on the fixture only")
    try:
        import psycopg2
        conn = psycopg2.connect(host=os.environ.get("DBT_HOST") or "localhost", port=int(port),
                                user=os.environ.get("DBT_USER") or "originba",
                                password=os.environ.get("DBT_PASSWORD") or "originba",
                                dbname=os.environ.get("DBT_DBNAME") or "originba_local", connect_timeout=3)
    except Exception as exc:  # noqa: BLE001
        raise unittest.SkipTest(f"no fixture warehouse: {exc}") from exc
    conn.set_session(readonly=True, autocommit=True)
    with conn.cursor() as cur:
        cur.execute("select to_regclass('reporting.agg_billed_charge_daily') is not null")
        if not cur.fetchone()[0]:
            conn.close()
            raise unittest.SkipTest("the aggregates are not built in this fixture warehouse")
    return conn


def _key(row):
    """A sort key that orders equal numbers equally whatever their type or scale."""
    return [(2, "") if v is None else (0, float(v), "") if isinstance(v, (int, float, Decimal))
            else (1, 0.0, str(v)) for v in row]


def _request(query):
    """What an explorer request carries of a card's or governed question's query (not its
    limit or ranking), and its filters."""
    return {"dimensions": query.get("dimensions") or [], "measures": query["measures"]}, list(query.get("filters") or [])


def cards(canvas, probes):
    """(name, request, filters, date field) for every card and governed question on the
    canvas, each question also with every parameter the canvas can express."""
    for kpi in [*EXECUTIVE_KPIS, *(k for ks in WORKSTREAM_KPIS.values() for k in ks)]:
        if kpi["snapshot_id"] == canvas:
            for part in ("value", "trend"):
                yield f"card {kpi['id']} {part}", *_request(kpi[part]), kpi.get("date_field")
    for metric in METRICS:
        if metric.snapshot_id == canvas and metric.build:
            spec = metric.build({})
            request, filters = _request(spec["query"])
            yield f"question {metric.id}", request, filters, spec.get("date_field")
            for key in metric.param_keys:
                if _PARAM_FIELDS.get(key) in probes:
                    field = _PARAM_FIELDS[key]
                    yield (f"question {metric.id} {key}", request,
                           [*filters, {"field": field, "op": "eq", "value": probes[field]}], spec.get("date_field"))


class AggregateParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _execute(self, sql, binds=None, *, max_rows=5000, **_):
        with self.conn.cursor() as cur:
            cur.execute(sql, binds or None)
            return [c[0] for c in cur.description], [list(r) for r in cur.fetchmany(max_rows)]

    def _rows(self, sql):
        with self.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    def setUp(self):
        self.patches = [mock.patch.object(se, "snapshot_backend", return_value=BACKEND),
                        mock.patch.object(ar, "snapshot_backend", return_value=BACKEND),
                        mock.patch.object(se, "data_version", return_value=None),
                        mock.patch("api.warehouse_db.execute_query", side_effect=self._execute)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        sc.clear()

    def _run(self, snapshot, request, filters):
        sc.clear()
        body = se.QueryRequest(**request, filters=filters)
        return se.cached_query("fixture", snapshot, body, filters)

    def _as_of(self, canvas, date_field):
        return self._rows(f'select max("{date_field}")::date from reporting.{canvas}')[0][0] or date.today()

    def _rules(self, canvas):
        # the commonest service type, and the rarest: the rare one empties most windows,
        # which is where a count over nothing (0) and a sum over nothing (NULL) part ways
        kinds = [r[0] for r in self._rows(f'select "Service Type", count(*) from reporting.{canvas} '
                                          'group by 1 order by 2 desc, 1') if r[0] is not None]
        return [None] + [[k] for k in dict.fromkeys([kinds[0], kinds[-1]])]

    def _probes(self, canvas, snapshot):
        """The commonest value of each governed-question parameter column the canvas carries."""
        fields = {f["id"] for f in snapshot["fields"]}
        out = {}
        for field in _PARAM_FIELDS.values():
            if field in fields:
                rows = self._rows(f'select "{field}" from reporting.{canvas} where "{field}" is not null '
                                  'group by 1 order by count(*) desc, 1 limit 1')
                if rows:
                    out[field] = rows[0][0]
        return out

    def requests(self, canvas, snapshot):
        """(name, request, filters, date field) for everything the portal asks of this canvas."""
        date_field = snapshot["default_date_field"]
        sums = list({m["field"]: {"field": m["field"], "agg": "sum"} for r in snapshot["premade_reports"]
                     for m in r["measures"] if m["agg"] == "sum"}.values())
        for report in snapshot["premade_reports"]:
            yield (f"report {report['id']}", {"dimensions": report["dimensions"], "measures": report["measures"]},
                   list(report.get("filters") or []), date_field)
        for name, request, filters, own_date in cards(canvas, self._probes(canvas, snapshot)):
            yield name, request, filters, own_date or date_field   # a question with none uses the canvas's
        yield "count by service type", {"dimensions": ["Service Type"], "measures": [COUNT]}, [], date_field
        yield "month trend", {"dimensions": [], "measures": [*sums, COUNT],
                              "time_dimensions": [{"field": date_field, "grain": "month"}]}, [], date_field
        yield "money total", {"dimensions": [], "measures": [COUNT, *sums]}, list(MONEY_FILTERS.get(canvas, [])), date_field

    def windows(self, date_field, as_of):
        for name in NAMED:
            yield name, [{"field": date_field, "op": "between", "value": preset_range(name, as_of)}]
        yield "fallback_180_days", [{"field": date_field, "op": "between", "value": preset_range(None, as_of)}]
        yield "all_time", []

    def test_routed_equals_unrouted_for_every_report_card_window_and_rule(self):
        for canvas in CANVASES:
            snapshot = SNAPSHOTS[canvas]
            unrouted = {k: v for k, v in snapshot.items() if k != "aggregate"}
            agg = (snapshot.get("aggregate") or {}).get("table")
            as_of, rules = self._as_of(canvas, snapshot["default_date_field"]), self._rules(canvas)
            cases = 0
            for name, request, request_filters, date_field in self.requests(canvas, snapshot):
                for window_name, window in self.windows(date_field, as_of):
                    for rule in rules:
                        filters = window + request_filters + ([{"field": "Service Type", "op": "in", "value": rule}] if rule else [])
                        with self.subTest(canvas=canvas, request=name, window=window_name, rule=rule):
                            routed_sql, routed_cols, routed, served = self._run(snapshot, request, filters)
                            canvas_sql, canvas_cols, plain, canvas_served = self._run(unrouted, request, filters)
                            self.assertEqual(served, agg, routed_sql)
                            self.assertEqual(canvas_served, canvas)
                            self.assertEqual(routed_cols, canvas_cols)
                            self.assertEqual(sorted(routed, key=_key), sorted(plain, key=_key))
                            self.assertEqual(routed, plain, "same rows, different order: the row limit would differ")
                            cases += 1
            print(f"\n{canvas}: {cases} cases, routed == unrouted, as of {as_of}")
            with self.subTest(canvas=canvas, check="case count"):
                self.assertGreaterEqual(cases, 40)

    def test_the_opening_report_routes(self):
        for canvas in CANVASES:
            snapshot = SNAPSHOTS[canvas]
            as_of = self._as_of(canvas, snapshot["default_date_field"])
            with self.subTest(canvas=canvas), mock.patch.object(se, "reporting_today", return_value=as_of):
                window = se._default_date_filter(snapshot)
                opening = snapshot["premade_reports"][0]
                request = {"dimensions": opening["dimensions"], "measures": opening["measures"]}
                filters = [window.model_dump(), *(opening.get("filters") or [])]
                _, _, routed, served = self._run(snapshot, request, filters)
                _, _, plain, _ = self._run({k: v for k, v in snapshot.items() if k != "aggregate"}, request, filters)
                self.assertEqual(served, (snapshot.get("aggregate") or {}).get("table"))
                self.assertEqual(routed, plain)


if __name__ == "__main__":
    unittest.main()
