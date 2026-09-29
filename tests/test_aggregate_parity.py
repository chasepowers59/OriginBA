"""Routed == unrouted, exactly, on a real warehouse built by dbt.

Runs every ready-to-run report on rpt_billed_charge, plus a count, a month trend and a
grand total, over every window the portal offers by name (last 30, 90 and 365 days as of
the data's last Bill Date) and all time, with no row rule and with Service Type rules,
twice through cached_query: once with the catalog's aggregate block (routed to
agg_billed_charge_daily) and once without it (the canvas). The rows must be identical,
in the same order, and the routed run must really have been served by the aggregate.

Needs the disposable fixture warehouse from originba_dbt (`dbt build --target local`,
port 5433) with the aggregate built. Reads the connection from the variables the dbt
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
from api.date_presets import preset_range  # noqa: E402

CANVAS = json.loads((ROOT / "tests" / "fixtures" / "catalog_dbt_aggregate.json").read_text())["snapshots"]["rpt_billed_charge"]
UNROUTED = {k: v for k, v in CANVAS.items() if k != "aggregate"}
AGG = CANVAS["aggregate"]["table"]
BACKEND = ("postgres", "postgres", "reporting")


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
        cur.execute(f"select to_regclass('reporting.{AGG}') is not null")
        if not cur.fetchone()[0]:
            conn.close()
            raise unittest.SkipTest(f"reporting.{AGG} is not built in this fixture warehouse")
    return conn


def _key(row):
    """A sort key that orders equal numbers equally whatever their type or scale."""
    return [(2, "") if v is None else (0, float(v), "") if isinstance(v, (int, float, Decimal))
            else (1, 0.0, str(v)) for v in row]


class AggregateParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()
        with cls.conn.cursor() as cur:
            cur.execute('select max("Bill Date")::date from reporting.rpt_billed_charge')
            cls.as_of = cur.fetchone()[0] or date.today()
            cur.execute('select "Service Type", count(*) from reporting.rpt_billed_charge '
                        'group by 1 order by 2 desc, 1')
            kinds = [r[0] for r in cur.fetchall() if r[0] is not None]
        # the commonest service type, and the rarest: the rare one empties most windows,
        # which is where a count over nothing (0) and a sum over nothing (NULL) part ways
        cls.rules = [None] + [[k] for k in dict.fromkeys([kinds[0], kinds[-1]])]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _execute(self, sql, binds=None, *, max_rows=5000, **_):
        with self.conn.cursor() as cur:
            cur.execute(sql, binds or None)
            return [c[0] for c in cur.description], [list(r) for r in cur.fetchmany(max_rows)]

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

    def requests(self):
        for report in CANVAS["premade_reports"]:
            yield report["id"], {"dimensions": report["dimensions"], "measures": report["measures"]}, report.get("filters") or []
        yield "count_by_service_type", {"dimensions": ["Service Type"], "measures": [{"field": "*", "agg": "count"}]}, []
        yield "monthly_trend", {"dimensions": [], "measures": [{"field": "Billed Amount", "agg": "sum"}, {"field": "*", "agg": "count"}],
                                "time_dimensions": [{"field": "Bill Date", "grain": "month"}]}, []
        yield "frozen_total", {"dimensions": [], "measures": [{"field": "*", "agg": "count"}, {"field": "Billed Amount", "agg": "sum"}]}, \
            [{"field": "Is Frozen", "op": "eq", "value": True}, {"field": "Is Cancelled", "op": "eq", "value": False}]

    def windows(self):
        for days in (30, 90, 365):
            yield f"last_{days}_days", [{"field": "Bill Date", "op": "between",
                                         "value": preset_range({"kind": "days", "days": days}, self.as_of)}]
        yield "all_time", []

    def test_routed_equals_unrouted_for_every_report_window_and_rule(self):
        cases = 0
        for name, request, report_filters in self.requests():
            for window_name, window in self.windows():
                for rule in self.rules:
                    filters = window + report_filters + ([{"field": "Service Type", "op": "in", "value": rule}] if rule else [])
                    with self.subTest(report=name, window=window_name, rule=rule):
                        routed_sql, routed_cols, routed, served = self._run(CANVAS, request, filters)
                        canvas_sql, canvas_cols, unrouted, canvas_served = self._run(UNROUTED, request, filters)
                        self.assertEqual(served, AGG, routed_sql)
                        self.assertEqual(canvas_served, "rpt_billed_charge")
                        self.assertEqual(routed_cols, canvas_cols)
                        self.assertEqual(sorted(routed, key=_key), sorted(unrouted, key=_key))
                        self.assertEqual(routed, unrouted, "same rows, different order: the row limit would differ")
                        cases += 1
        print(f"\naggregate parity: {cases} cases, routed == unrouted, as of {self.as_of}")
        self.assertGreaterEqual(cases, 40)


if __name__ == "__main__":
    unittest.main()
