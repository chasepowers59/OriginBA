"""KPI cards answer from a canvas's pre-aggregate when the answer is provably the same.

The explorer routed through api/aggregate_routing.py; the KPI runner built its SQL against the
canvas every time. CityCorp's "GL distribution lines" card grouped 2.7M rpt_gl rows by GL
account in 85.6 s, past the 60 s call timeout ("This figure took too long to load"), while
AGG_GL_DAILY held the same answer in 22,459 rows (2026-10-01). The routing rules are the
explorer's, unchanged: anything not provably equal still reads the canvas."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import kpi_runner as kr  # noqa: E402

SPEC = {"dimensions": ["GL Account"], "measures": [{"field": "*", "agg": "count"}], "filters": [], "limit": 6}


class KpiRoutingTests(unittest.TestCase):
    def _run(self, routed, spec=SPEC, fail_routed=False):
        ran = []

        def execute(sql, binds=None, *, organization_id, max_rows):
            ran.append(sql)
            if fail_routed and sql == "ROUTED":
                raise RuntimeError("ORA-00904")
            return ["GL Account", "m0"], [["01-050-142000", 667696]]
        with mock.patch.object(kr, "snapshot_backend", return_value=("oracle", "oracle_dbt", "ORIGINBA_REPORTING")), \
             mock.patch.object(kr, "execute_query", side_effect=execute), \
             mock.patch("api.aggregate_routing.routed_query", return_value=routed) as rq:
            kr.run_kpi_query("rpt_gl", spec, "Accounting Date", "2025-07-17", "2026-07-17", organization_id="citycorp")
        return ran, rq

    def test_a_provably_equal_aggregate_answers_the_card(self):
        ran, rq = self._run(("ROUTED", {}, "agg_gl_daily"))
        self.assertEqual(ran, ["ROUTED"])
        self.assertEqual(rq.call_args.kwargs["filters"][-1]["field"], "Accounting Date")   # the card's window

    def test_no_routing_reads_the_canvas(self):
        ran, _ = self._run(None)
        self.assertEqual(len(ran), 1)
        self.assertNotEqual(ran[0], "ROUTED")

    def test_an_aggregate_that_cannot_answer_falls_back_to_the_canvas(self):
        ran, _ = self._run(("ROUTED", {}, "agg_gl_daily"), fail_routed=True)
        self.assertEqual(ran[0], "ROUTED")
        self.assertNotEqual(ran[1], "ROUTED")

    def test_a_magnitude_ranking_is_never_routed(self):
        ran, rq = self._run(("ROUTED", {}, "agg_gl_daily"), spec={**SPEC, "rank": "magnitude"})
        rq.assert_not_called()
        self.assertNotEqual(ran[0], "ROUTED")


if __name__ == "__main__":
    unittest.main()
