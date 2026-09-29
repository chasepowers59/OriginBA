"""Bugs found by the 2026-09-29 bug hunt (docs/PORTAL_ISSUES_LOG.md B-1..B-4, B-8, B-9), each
pinned by the reproduction that found it.

- B-1: an embed link is refused for a canvas its creator's workstreams do not reach, when it is
  made and every time it is served.
- B-2: a summary whose cards all failed to connect (or found no warehouse) is never cached; the
  page must recover as soon as the database does, not after the next rebuild.
- B-3: an embed shows the view the way it was saved: its named window (kept relative), a custom
  range, its scope and its ready-to-run report's own filters; "All dates" has no window.
- B-4: the alert list shows only alerts on views the caller can see and canvases they may open.
- B-8: the warmer thread survives any error in one organization's pass.
- B-9: a warm pass that failed is retried on the next pass, not after the next rebuild.
- B-13: the saved-view list keeps to the canvases the caller's workstreams reach.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import cache_warmer as cw  # noqa: E402
from api import embed  # noqa: E402
from api import executive_dashboard as ed  # noqa: E402
from api import portal_routes as pr  # noqa: E402
from api import saved_views as sv  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api import summary_cache  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

SECRET = "x" * 40


def _ctx(uid, workstreams=("*",), role="editor", rules=()):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id="dev",
                       organization_id="dev", organization_name="Dev",
                       permissions={"portal:read", "saved_views:write"}, workstreams=list(workstreams),
                       row_rules=tuple(rules))


class EmbedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.executed = []

        def run(sql, binds=None, **_):
            self.executed.append((sql, binds))
            return ["Bill Cycle", "m0"], [["C1", 1.0]]
        self.patches = [
            mock.patch.dict(os.environ, {"PORTAL_AUTH_SECRET": SECRET}),
            mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
            mock.patch.object(sv._pss, "enabled", return_value=False),
            mock.patch("api.snapshot_catalog.snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch("api.warehouse_db.execute_query", side_effect=run),
            mock.patch("api.access_audit.record_access_event"),
            mock.patch("api.row_security.auth_disabled", return_value=True),
            mock.patch.object(embed, "data_version", return_value=None),
            mock.patch.object(embed, "data_as_of", return_value="2026-09-28"),
        ]
        for p in self.patches:
            p.start()
        summary_cache.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _view(self, ctx, **kw):
        base = dict(snapshot_id="rpt_bill_segment", snapshot_label="Bill Segment", title="Billed by cycle",
                    kind="custom", dimensions=["Bill Cycle"], measures=[{"field": "Billed Amount", "agg": "sum"}])
        return pr.post_saved_view(pr.SavedViewCreate(**{**base, **kw}), ctx=ctx)

    def test_b1_an_embed_is_refused_for_a_canvas_outside_the_creators_workstreams(self):
        billing_only = _ctx("bob", workstreams=["billing"])
        view = self._view(_ctx("alice"), snapshot_id="rpt_sa_aged_balance", snapshot_label="Aged balance",
                          dimensions=["Bill Cycle"], measures=[{"field": "Total Arrears", "agg": "sum"}])
        # an ownerless legacy view: any writer may edit it, so only the grant can stop this
        legacy = {**view, "owner_id": None, "owner_email": None}
        with mock.patch.object(embed, "_find_view", return_value=legacy):
            with self.assertRaises(HTTPException) as err:
                embed.create_embed_token(embed.EmbedTokenRequest(view_id=view["id"]), ctx=billing_only)
        self.assertEqual(err.exception.status_code, 403)

    def test_b1_a_served_embed_stops_when_the_creator_loses_the_workstream(self):
        view = self._view(_ctx("alice"))
        token = embed.create_embed_token(embed.EmbedTokenRequest(view_id=view["id"]), ctx=_ctx("alice"))["token"]
        with mock.patch("api.row_security.auth_disabled", return_value=False), \
             mock.patch("api.row_security._user_record",
                        return_value={"is_active": True, "role": "editor", "row_rules": [], "workstreams": ["field_ops"]}):
            with self.assertRaises(HTTPException) as err:
                embed.embed_data(token)
        self.assertEqual(err.exception.status_code, 403)

    def _embedded_sql(self, **kw):
        view = self._view(_ctx("alice"), **kw)
        token = embed.create_embed_token(embed.EmbedTokenRequest(view_id=view["id"]), ctx=_ctx("alice"))["token"]
        embed.embed_data(token)
        return self.executed[-1]

    def test_b3_a_named_window_stays_relative_and_scope_applies(self):
        sql, binds = self._embedded_sql(date_preset="Last 12 months", date_start="2025-01-01", date_end="2025-12-31",
                                        scope_field="Service Type", scope_value="Water")
        values = json.dumps(binds, default=str)
        self.assertIn("2025-09-28", values)       # as of 2026-09-28, 365 days back: not the saved 2025 dates
        self.assertNotIn("2025-01-01", values)
        self.assertIn('"Service Type"', sql)

    def test_b3_a_custom_range_is_kept_and_all_dates_has_no_window(self):
        _, binds = self._embedded_sql(date_preset="Custom range", date_start="2026-01-01", date_end="2026-03-31")
        self.assertIn("2026-01-01", json.dumps(binds, default=str))
        sql, binds = self._embedded_sql(date_preset="All dates", date_start="2026-01-01", date_end="2026-03-31")
        self.assertNotIn("2026-01-01", json.dumps(binds, default=str))

    def test_b3_a_ready_to_run_reports_own_filters_apply(self):
        snapshot = se.get_snapshot("rpt_bill_segment", "dev")
        report = next(r for r in snapshot["premade_reports"] if r.get("filters"))
        sql, _ = self._embedded_sql(kind="premade", report_id=report["id"], dimensions=report["dimensions"],
                                    measures=report["measures"])
        self.assertIn(f'"{report["filters"][0]["field"]}"', sql)


class SummaryCacheTests(unittest.TestCase):
    def test_b2_a_page_of_connection_failures_is_not_cached(self):
        summary_cache.clear()
        state = {"down": True}

        def kpi(k, **_):
            if state["down"]:
                return {"id": k["id"], "label": k["label"], "value": None, "error": "could not connect to server"}
            return {"id": k["id"], "label": k["label"], "value": 42, "error": None, "trend": []}
        with mock.patch.object(se, "data_version", return_value="stamp-V1"), \
             mock.patch.object(ed, "demo_configured", return_value=True), \
             mock.patch.object(ed, "available_kpis", side_effect=lambda k, o: (k, None)), \
             mock.patch.object(ed, "only_readable", side_effect=lambda k, r, o: k), \
             mock.patch.object(ed, "execute_kpi_definition", side_effect=kpi), \
             mock.patch.object(ed, "_refresh_insight", return_value=None):
            first = se.cached_home_summary("ellensburg", 30, False, "prior_period", [], ["*"], {}, ())
            self.assertEqual(first["kpis"], [])
            state["down"] = False
            second = se.cached_home_summary("ellensburg", 30, False, "prior_period", [], ["*"], {}, ())
        self.assertTrue(second["kpis"])


class AlertListTests(unittest.TestCase):
    def test_b4_the_alert_list_hides_what_the_caller_cannot_see(self):
        from api import kpi_alert_routes as kr
        alerts = [
            {"id": "a1", "kpi_id": "billed_revenue", "saved_view_id": None, "kpi_label": "Billed revenue"},
            {"id": "a2", "kpi_id": None, "saved_view_id": "private-v", "kpi_label": "Mine"},
            {"id": "a3", "kpi_id": None, "saved_view_id": "debt-v", "kpi_label": "Debt"},
            {"id": "a4", "kpi_id": None, "saved_view_id": "billing-v", "kpi_label": "Billing"},
        ]
        views = {"private-v": {"id": "private-v", "snapshot_id": "rpt_bill_segment", "visibility": "private", "owner_id": "ana"},
                 "debt-v": {"id": "debt-v", "snapshot_id": "rpt_sa_aged_balance", "visibility": "organization"},
                 "billing-v": {"id": "billing-v", "snapshot_id": "rpt_bill_segment", "visibility": "organization"}}
        with mock.patch.object(kr, "require_org_for_data", return_value="dev"), \
             mock.patch.object(kr.ka, "list_alerts", return_value=alerts), \
             mock.patch("api.report_schedules._find_view", side_effect=lambda vid, org: views.get(vid)), \
             mock.patch("api.auth.workstream_access.snapshot_workstream",
                        side_effect=lambda sid, org=None: "debt" if "aged" in sid else "billing"):
            ids = [a["id"] for a in kr.get_alerts(ctx=_ctx("bob", workstreams=["billing"]))["alerts"]]
        self.assertEqual(ids, ["a1", "a4"])


class SavedViewListTests(unittest.TestCase):
    """B-13: the saved-view list keeps to the canvases the caller's workstreams reach."""

    def test_b13_views_on_ungranted_canvases_are_not_listed(self):
        views = [{"id": "v1", "snapshot_id": "rpt_bill_segment", "visibility": "organization"},
                 {"id": "v2", "snapshot_id": "rpt_sa_aged_balance", "visibility": "organization"}]
        with mock.patch.object(pr, "list_saved_views", return_value=views), \
             mock.patch("api.auth.workstream_access.snapshot_workstream",
                        side_effect=lambda sid, org=None: "debt" if "aged" in sid else "billing"):
            out = pr.get_saved_views(ctx=_ctx("bob", workstreams=["billing"]))
        self.assertEqual([v["id"] for v in out["views"]], ["v1"])


class WarmerTests(unittest.TestCase):
    def setUp(self):
        cw.reset()

    def test_b9_a_failed_pass_is_retried(self):
        calls = {"n": 0}

        def home(*a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ConnectionError("could not connect to server")
            return {"kpis": []}
        with mock.patch.object(cw, "data_version", return_value="V2"), \
             mock.patch.object(cw, "_workstreams", return_value=[]), \
             mock.patch.object(cw, "_opening_reports", return_value=[]), \
             mock.patch.object(se, "cached_home_summary", side_effect=home), \
             self.assertLogs("originba.api", level="WARNING"):
            self.assertEqual(cw.warm_once("ellensburg"), [])
            self.assertEqual(cw.warm_once("ellensburg"), ["home"])

    def test_b8_the_thread_survives_an_error_in_one_pass(self):
        n = {"calls": 0}

        def workstreams(org):
            n["calls"] += 1
            if n["calls"] == 1:
                raise json.JSONDecodeError("Expecting value", "", 0)
            return []
        versions = iter(["V1", "V2", "V3", "V4", "V5", "V6"])
        stop = threading.Event()
        with mock.patch.object(cw, "INTERVAL_SECONDS", 0.05), \
             mock.patch.object(cw, "_organizations", return_value=["ellensburg"]), \
             mock.patch.object(cw, "data_version", side_effect=lambda o: next(versions, "V6")), \
             mock.patch.object(cw, "_workstreams", side_effect=workstreams), \
             mock.patch.object(cw, "_opening_reports", return_value=[]), \
             mock.patch.object(se, "cached_home_summary", return_value={}), \
             self.assertLogs("originba.api", level="WARNING"):
            t = threading.Thread(target=cw._loop, args=(stop,), daemon=True)
            t.start()
            time.sleep(0.4)
            alive = t.is_alive()
            stop.set()
        self.assertTrue(alive)
        self.assertGreater(n["calls"], 1)


if __name__ == "__main__":
    unittest.main()
