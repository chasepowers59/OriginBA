"""Ori's first proactive surface: "Ori found something worth investigating".

From the home cards' own vetted figures (the same KPI runner the dashboard uses), compared
with the prior period, Ori names the large moves: at least 15% up or down, with enough
behind it to matter (a count of at least 20, or money of at least 1,000 in either period),
on cards that are windowed (a balance or a population has no prior period). A missing
value, a failed card or a zero prior never becomes a finding. At most three, largest first,
each worded in plain numbers with the question to ask Ori next.

The bar is 15%: at 25% Ori stayed silent on Ellensburg's billed revenue falling 17.9%
($3.36M vs $4.09M, measured 2026-09-29), which is exactly what a finance lead wants raised.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.ori_insights import findings  # noqa: E402


def kpi(**kw):
    base = {"id": "billed", "label": "Billed revenue", "format": "currency", "value": 700.0, "prior_value": 1000.0,
            "change_pct": -30.0, "compare_label": "vs prior 30 days", "error": None}
    return {**base, **kw}


class FindingTests(unittest.TestCase):
    def test_a_large_move_is_a_finding_in_plain_words(self):
        [f] = findings({"kpis": [kpi()]})
        self.assertEqual(f["kpi_id"], "billed")
        self.assertEqual(f["headline"], "Billed revenue: down 30% vs prior 30 days")
        self.assertEqual(f["detail"], "$700.00 now, $1,000.00 before.")
        self.assertEqual(f["question"], "Why did billed revenue go down 30% vs prior 30 days? What changed?")

    def test_small_moves_and_thin_volume_are_not_findings(self):
        self.assertEqual(findings({"kpis": [kpi(value=900.0, change_pct=-10.0)]}), [])
        self.assertEqual(findings({"kpis": [kpi(value=300.0, prior_value=500.0, change_pct=-40.0)]}), [])
        self.assertEqual(findings({"kpis": [kpi(format="number", value=4, prior_value=10, change_pct=-60.0)]}), [])

    def test_no_finding_from_missing_failed_or_windowless_cards(self):
        for bad in (kpi(value=None), kpi(prior_value=None), kpi(change_pct=None), kpi(error="could not connect"),
                    kpi(prior_value=0.0), kpi(compare_label=None)):
            self.assertEqual(findings({"kpis": [bad]}), [], bad)

    def test_a_large_money_drop_under_a_quarter_is_raised(self):
        [f] = findings({"kpis": [kpi(value=3359173.66, prior_value=4092306.21, change_pct=-17.9)]})
        self.assertEqual(f["headline"], "Billed revenue: down 18% vs prior 30 days")

    def test_at_most_three_largest_first(self):
        cards = [kpi(id=f"k{i}", label=f"Card {i}", value=1000.0 + 100 * i, prior_value=1000.0, change_pct=10.0 * i)
                 for i in range(3, 8)]
        self.assertEqual([f["kpi_id"] for f in findings({"kpis": cards})], ["k7", "k6", "k5"])

    def test_plural_labels_and_names_read_right(self):
        # Ellensburg 2026-09-29: "Usage transactions is down 71%", "to Do entries created rose 16%"
        [f] = findings({"kpis": [kpi(label="Usage transactions", format="number", value=30, prior_value=100, change_pct=-70.0)]})
        self.assertEqual(f["headline"], "Usage transactions: down 70% vs prior 30 days")
        self.assertEqual(f["question"], "Why did usage transactions go down 70% vs prior 30 days? What changed?")
        from api.ori_insights import brief
        read = brief({"period": {"label": "Last 30 days", "days": 30},
                      "kpis": [kpi(label="To Do entries created", format="number", value=116, prior_value=100, change_pct=16.0)]})
        self.assertIn("To Do entries created rose 16%", read)

    def test_counts_read_as_counts(self):
        [f] = findings({"kpis": [kpi(format="number", label="Bills completed", value=150, prior_value=100, change_pct=50.0)]})
        self.assertEqual(f["headline"], "Bills completed: up 50% vs prior 30 days")
        self.assertEqual(f["detail"], "150 now, 100 before.")


if __name__ == "__main__":
    unittest.main()


class RouteTests(unittest.TestCase):
    def _ctx(self, rules=()):
        from api.auth.dependencies import AuthContext
        return AuthContext(id="u", email="u@utility.gov", display_name="u", role="editor", client_id="dev",
                           organization_id="dev", organization_name="Dev", permissions={"snapshots:read"},
                           workstreams=["*"], row_rules=tuple(rules))

    def test_findings_come_from_the_home_summary_in_compare_mode(self):
        from unittest import mock
        from api import ori_routes
        with mock.patch.object(ori_routes, "require_org_for_data", return_value="dev"), \
             mock.patch("api.snapshot_explorer.cached_home_summary", return_value={"kpis": [kpi()], "period": {"days": 30}}) as home:
            out = ori_routes.ori_findings(ctx=self._ctx())
        self.assertEqual(home.call_args.args[:5], ("dev", 30, True, "prior_period", []))
        self.assertEqual([f["kpi_id"] for f in out["findings"]], ["billed"])

    def test_a_workstream_page_reads_its_own_cards(self):
        from unittest import mock
        from fastapi import HTTPException
        from api import ori_routes
        summary = {"kpis": [kpi()], "period": {"label": "Last 30 days", "days": 30}}
        with mock.patch.object(ori_routes, "require_org_for_data", return_value="dev"), \
             mock.patch("api.snapshot_explorer.cached_workstream_summary", return_value=summary) as ws, \
             mock.patch("api.snapshot_explorer.cached_home_summary") as home:
            out = ori_routes.ori_findings(workstream="billing", ctx=self._ctx())
            home.assert_not_called()
            self.assertEqual(ws.call_args.args[:5], ("dev", "billing", 30, True, "prior_period"))
            self.assertEqual([f["kpi_id"] for f in out["findings"]], ["billed"])
            self.assertTrue(out["brief"])
            import dataclasses
            finance_only = dataclasses.replace(self._ctx(), workstreams=["finance"])
            with self.assertRaises(HTTPException) as denied:
                ori_routes.ori_findings(workstream="billing", ctx=finance_only)
            self.assertEqual(denied.exception.status_code, 403)

    def test_a_restricted_reader_gets_none(self):
        from api import ori_routes
        out = ori_routes.ori_findings(ctx=self._ctx(rules=({"field": "Service Type", "values": ["Water"]},)))
        self.assertEqual(out["findings"], [])


class WarmTests(unittest.TestCase):
    def test_the_warmer_builds_the_compare_summary_too(self):
        from unittest import mock
        from api import cache_warmer as cw
        cw.reset()
        with mock.patch.object(cw, "data_version", return_value="V1"), \
             mock.patch.object(cw, "_workstreams", return_value=[]), \
             mock.patch.object(cw, "_opening_reports", return_value=[]), \
             mock.patch("api.ori_series.cached_history", return_value=({}, {})), \
             mock.patch("api.dq_routes.warm"), \
             mock.patch("api.snapshot_explorer.cached_home_summary", return_value={"kpis": []}) as home:
            built = cw.warm_once("dev")
        self.assertIn("ori findings", built)
        self.assertIn(True, [c.args[2] for c in home.call_args_list])
