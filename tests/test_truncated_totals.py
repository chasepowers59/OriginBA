"""A breakdown cut to its top rows still reports the TRUE total.

The query API answers a breakdown with at most 500 groups (the top ones by the measure). The
explorer then totalled the rows it got: CityCorp's "Which service points are switched on and off
most?" (2026-10-01) showed TOTAL RECORDS 1,971, a footer total of 1,971 and "0.6% of the 1,971
total" over 500 premises, when the period held 3,591 events. When an answer is cut, the API now
says so (`truncated`) and answers the same question unbroken (`totals`), so the total and every
share are the real ones."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import snapshot_explorer as se  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

CTX = AuthContext(id="u", email="u@utility.gov", display_name="u", role="editor", client_id="dev",
                  organization_id="dev", organization_name="Dev", permissions={"snapshots:query"}, workstreams=["*"])


class TruncatedTotalsTests(unittest.TestCase):
    def _run(self, groups: int, limit: int = 500):
        calls = []

        def cached_query(org_id, snapshot, request, filters):
            calls.append(request)
            if request.dimensions or request.time_dimensions:
                return "select ...", ["Premise Address", "m0"], [[f"p{i}", 1] for i in range(min(groups, request.limit))], "t"
            return "select ...", ["m0"], [[groups * 3]], "t"     # the unbroken answer
        snapshot = se.get_snapshot("rpt_bill_segment", "dev")
        with mock.patch.object(se, "require_org_for_data", return_value="dev"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=snapshot), \
             mock.patch.object(se, "cached_query", side_effect=cached_query), \
             mock.patch("api.access_audit.record_access_event"):
            out = se.snapshot_query("rpt_bill_segment", se.QueryRequest(
                dimensions=["SA Type"], measures=[{"field": "*", "agg": "count"}], all_dates=True, limit=limit), ctx=CTX)
        return out, calls

    def test_a_cut_breakdown_says_so_and_carries_the_true_total(self):
        out, calls = self._run(groups=900)
        self.assertEqual(out["row_count"], 500)
        self.assertTrue(out["truncated"])
        self.assertEqual(out["totals"], {"m0": 2700})
        self.assertEqual(calls[1].dimensions, [])            # the same question, unbroken
        self.assertEqual(calls[1].measures, calls[0].measures)

    def test_a_whole_breakdown_asks_nothing_more(self):
        out, calls = self._run(groups=37)
        self.assertFalse(out["truncated"])
        self.assertIsNone(out["totals"])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
