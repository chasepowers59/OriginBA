""""All dates" means all dates. The API adds a trailing default window to an unfiltered query
on a large canvas (so a careless request cannot scan millions of rows), and it said so in
applied_window. But a reader who CHOSE "All dates" in the explorer sent no filters and got
that window anyway: the aged-balance page showed "No data" under a large record count. The
request now says `all_dates: true`, and then no window is added."""
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
WINDOW = se.FilterRequest(field="Bill Date", op="between", value=["2026-06-30", "2026-09-28"])


class AllDatesTests(unittest.TestCase):
    def _run(self, **body):
        seen = {}

        def cached_query(org_id, snapshot, request, filters):
            seen["filters"] = filters
            return "select 1", ["m0"], [[1]]
        snapshot = se.get_snapshot("rpt_bill_segment", "dev")
        with mock.patch.object(se, "require_org_for_data", return_value="dev"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=snapshot), \
             mock.patch.object(se, "_default_date_filter", return_value=WINDOW), \
             mock.patch.object(se, "cached_query", side_effect=cached_query), \
             mock.patch("api.access_audit.record_access_event"):
            out = se.snapshot_query("rpt_bill_segment", se.QueryRequest(**body), ctx=CTX)
        return seen["filters"], out["applied_window"]

    def test_an_unfiltered_request_still_gets_the_announced_default_window(self):
        filters, applied = self._run()
        self.assertEqual(filters[0]["field"], "Bill Date")
        self.assertIsNotNone(applied)

    def test_all_dates_gets_no_window(self):
        filters, applied = self._run(all_dates=True)
        self.assertEqual(filters, [])
        self.assertIsNone(applied)


if __name__ == "__main__":
    unittest.main()


class MeasureLabelTests(unittest.TestCase):
    """A measure whose name already starts with its aggregate's word is not prefixed twice
    ("Total Total Balance" in the explorer and the builder)."""

    def test_no_doubled_prefix(self):
        snapshot = {"fields": [{"id": "Total Balance"}, {"id": "Billed Amount"}]}
        labels = se._result_labels(snapshot, ["m0", "m1"], [], [{"field": "Total Balance", "agg": "sum"},
                                                               {"field": "Billed Amount", "agg": "sum"}], [])
        self.assertEqual((labels["m0"], labels["m1"]), ("Total Balance", "Total Billed Amount"))
