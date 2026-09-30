"""Every ready-to-run report agrees with itself as the reader moves around it.

A report is answered again, differently, every time the reader acts: a breakdown, the same
number unbroken, a month trend, a click on one bar to cross-filter. Each must agree with the
others, through the same path the explorer uses (snapshot_explorer.cached_query), for every
report the catalog offers:

  1. the breakdown adds up to the total            (sum and count)
  2. the month trend adds up to the total          (sum and count, on the canvas's date)
  3. filtering to a bar reproduces that bar        (every aggregation: sum, count, avg, share, max)
  4. a share lies in 0-100; a group's average lies between its lowest and highest value

Runs on the disposable fixture warehouse built by originba_dbt (`dbt build --target local`,
port 5433), read-only, with the connection tests/test_aggregate_parity.py uses; skips when it
is not there. Never 5432, which holds real client data.
"""
from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import aggregate_routing as ar  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache as sc  # noqa: E402
from tests.test_aggregate_parity import BACKEND, _connect  # noqa: E402

CATALOG = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["snapshots"]
ADDITIVE = {"sum", "count"}
LIMIT = 5000


def _num(v):
    return None if v is None else float(v) if isinstance(v, (int, float, Decimal)) else v


def _close(a, b):
    a, b = _num(a) or 0.0, _num(b) or 0.0
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


class ReportInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = _connect()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def _execute(self, sql, binds=None, *, max_rows=LIMIT, **_):
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

    def run_query(self, snapshot, filters, dimensions=(), measures=None, time_dimensions=()):
        sc.clear()
        body = se.QueryRequest(dimensions=list(dimensions), measures=measures, filters=filters,
                               time_dimensions=list(time_dimensions), limit=LIMIT)
        _, _, rows, _ = se.cached_query("fixture", snapshot, body, filters)
        return rows

    def test_every_report_agrees_with_itself(self):
        cases, checked = 0, {"breakdown": 0, "trend": 0, "cross-filter": 0}
        for sid, snapshot in sorted(CATALOG.items()):
            for report in snapshot.get("premade_reports") or []:
                measure, dims = report["measures"][0], report["dimensions"]
                agg, filters = measure["agg"], list(report.get("filters") or [])
                with self.subTest(report=f"{sid}.{report['id']}"):
                    grouped = self.run_query(snapshot, filters, dims, [measure])
                    if len(grouped) >= LIMIT:
                        continue   # a truncated breakdown cannot add up
                    values = {tuple(r[:-1]): r[-1] for r in grouped}
                    if agg in ADDITIVE:
                        total = self.run_query(snapshot, filters, (), [measure])[0][-1]
                        self.assertTrue(_close(sum(_num(v) or 0 for v in values.values()), total),
                                        "the breakdown does not add up to the total")
                        checked["breakdown"] += 1
                        date = snapshot.get("default_date_field")
                        if date:
                            trend = self.run_query(snapshot, filters, (), [measure],
                                                   [{"field": date, "grain": "month"}])
                            self.assertTrue(_close(sum(_num(r[-1]) or 0 for r in trend), total),
                                            "the month trend does not add up to the total")
                            checked["trend"] += 1
                    if agg == "share":
                        self.assertTrue(all(0 <= (_num(v) or 0) <= 100 for v in values.values()))
                    top = next((k for k, v in sorted(values.items(), key=lambda kv: -(_num(kv[1]) or 0))
                                if k[0] is not None), None)
                    if top is not None:
                        drill = [*filters, {"field": dims[0], "op": "eq", "value": top[0]}]
                        clicked = self.run_query(snapshot, drill, (), [measure])[0][-1]
                        self.assertTrue(_close(clicked, values[top]), f"filtering to {top[0]!r} changed its value")
                        checked["cross-filter"] += 1
                        if agg == "avg":
                            lo, hi = self.run_query(snapshot, drill, (), [{"field": measure["field"], "agg": "min"},
                                                                          {"field": measure["field"], "agg": "max"}])[0]
                            self.assertTrue(_num(lo) - 1e-9 <= _num(clicked) <= _num(hi) + 1e-9)
                    cases += 1
        print(f"\n{cases} reports agree with themselves: {checked}")
        self.assertGreater(cases, 50)
        self.assertGreater(min(checked.values()), 30, checked)   # a fixture that empties the canvases proves nothing


if __name__ == "__main__":
    unittest.main()
