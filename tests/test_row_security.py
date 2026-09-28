"""Row-level security within an organization: a person limited to part of the data sees only it.

A user may carry row rules, e.g. [{"field": "Service Type", "values": ["Water"]}]. Every
governed query adds each rule as an IN filter. Fail closed: a canvas that does not carry a
rule's column is refused to that person (and left out of their catalog), never shown whole.
Raw SQL (the SQL workspace, the explorer's raw panel, the assistant) and the data quality
worklist cannot be filtered safely, so they are refused to a restricted person with a
sentence saying why. A schedule keeps its creator's rules.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import row_security as rsec  # noqa: E402
from api import snapshot_explorer as se  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

WATER = ({"field": "Service Type", "values": ["Water"]},)
PERMS = {"snapshots:read", "snapshots:query", "snapshots:raw_sql", "database:sql", "nlq:read", "portal:read",
         "saved_views:write"}


def _ctx(rules=()):
    return AuthContext(id="u1", email="u1@utility.gov", display_name="u1", role="editor", client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions=set(PERMS), workstreams=["*"],
                       row_rules=tuple(rules))


class RuleTests(unittest.TestCase):
    def test_a_rule_becomes_an_in_filter(self):
        snap = {"fields": [{"id": "Service Type"}, {"id": "Billed Amount"}]}
        self.assertEqual(rsec.row_filters(WATER, snap), [{"field": "Service Type", "op": "in", "value": ["Water"]}])

    def test_a_canvas_without_the_column_is_refused(self):
        with self.assertRaises(rsec.RowAccessDenied):
            rsec.row_filters(WATER, {"fields": [{"id": "Rate Schedule"}]})

    def test_rules_are_validated(self):
        self.assertEqual(rsec.clean_rules([{"field": " Service Type ", "values": ["Water", "Water", " "]}]),
                         [{"field": "Service Type", "values": ["Water"]}])
        for bad in ([{"field": "", "values": ["x"]}], [{"field": "A", "values": []}], [{"values": ["x"]}], "nope"):
            with self.assertRaises(ValueError):
                rsec.clean_rules(bad)


class EnforcementTests(unittest.TestCase):
    def setUp(self):
        self.executed = []

        def run(sql, binds=None, **_):
            self.executed.append((sql, binds))
            return ["m0"], [[1]]
        self.patches = [
            mock.patch.object(se, "require_org_for_data", return_value="dev"),
            mock.patch.object(se, "snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch("api.warehouse_db.execute_query", side_effect=run),
            mock.patch("api.access_audit.record_access_event"),
        ]
        for p in self.patches:
            p.start()
        from api import summary_cache
        summary_cache.clear()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _query(self, ctx, canvas="rpt_bill_segment"):
        body = se.QueryRequest(dimensions=[], measures=[{"field": "Billed Amount", "agg": "sum"}],
                               filters=[{"field": "Is Frozen", "op": "eq", "value": True}])
        return se.snapshot_query(canvas, body, ctx=ctx)

    def test_every_query_carries_the_rule(self):
        self._query(_ctx(WATER))
        sql, binds = self.executed[-1]
        self.assertIn('"Service Type" IN', sql)
        self.assertIn("Water", list(binds.values()))

    def test_an_unrestricted_person_is_unchanged(self):
        self._query(_ctx())
        self.assertNotIn("Service Type", self.executed[-1][0])

    def test_a_canvas_without_the_column_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            self._query(_ctx(WATER), canvas="rpt_rate_configuration")
        self.assertEqual(err.exception.status_code, 403)

    def test_the_catalog_leaves_out_canvases_they_cannot_read(self):
        ids = {s["id"] for s in se.snapshots_index(ctx=_ctx(WATER))["snapshots"]}
        self.assertIn("rpt_bill_segment", ids)
        self.assertNotIn("rpt_rate_configuration", ids)

    def test_the_record_count_is_their_count(self):
        se._STATS_CACHE.clear()
        out = se.snapshot_stats("rpt_bill_segment", ctx=_ctx(WATER))
        self.assertIn('"Service Type" IN', self.executed[-1][0])
        self.assertEqual(out["row_count"], 1)

    def test_value_lists_show_only_their_values(self):
        with mock.patch.object(se, "_row_estimate", return_value=10):
            se.snapshot_scope_options("rpt_bill_segment", "Bill Cycle", ctx=_ctx(WATER))
        self.assertIn('"Service Type" IN', self.executed[-1][0])

    def test_the_row_preview_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            se.snapshot_sample_rows("rpt_bill_segment", ctx=_ctx(WATER))
        self.assertEqual(err.exception.status_code, 403)

    def test_raw_sql_is_refused_everywhere(self):
        from api import database_routes as dr
        from api.assistant_routes import AskRequest, ask
        with self.assertRaises(HTTPException) as a:
            se.snapshot_raw_sql("rpt_bill_segment", se.RawSqlRequest(sql="select 1"), ctx=_ctx(WATER))
        with self.assertRaises(HTTPException) as b:
            dr.execute_sql(dr.SqlExecuteRequest(sql="select 1"), ctx=_ctx(WATER))
        with self.assertRaises(HTTPException) as c:
            ask(AskRequest(question="how much?"), ctx=_ctx(WATER))
        # The row count of arbitrary SQL answers questions one bit at a time (security review,
        # 2026-09-28: critical), and the table list gives whole-table row counts.
        with self.assertRaises(HTTPException) as d:
            dr.count_sql(dr.SqlExecuteRequest(sql="select 1"), ctx=_ctx(WATER))
        with self.assertRaises(HTTPException) as e:
            dr.list_tables(ctx=_ctx(WATER))
        for err in (a, b, c, d, e):
            self.assertEqual(err.exception.status_code, 403)
            self.assertIn("limited to part of the data", err.exception.detail)

    def test_the_data_quality_worklist_is_refused(self):
        from api import dq_routes
        with mock.patch.object(dq_routes, "require_org_for_data", return_value="dev"):
            with self.assertRaises(HTTPException) as err:
                dq_routes.dq_findings(ctx=_ctx(WATER))
        self.assertEqual(err.exception.status_code, 403)

    def test_home_cards_on_canvases_they_cannot_read_are_left_out(self):
        from api.executive_dashboard import build_executive_summary
        with mock.patch("api.executive_dashboard.warehouse_configured", return_value=True), \
             mock.patch("api.executive_dashboard.demo_configured", return_value=False), \
             mock.patch("api.executive_dashboard._refresh_insight", return_value=None):
            out = build_executive_summary(30, organization_id="dev", row_rules=WATER)
        from api.snapshot_catalog import get_snapshot
        for kpi in out["kpis"]:
            self.assertTrue(any(f["id"] == "Service Type" for f in get_snapshot(kpi["snapshot_id"], "dev")["fields"]),
                            kpi["id"])
        self.assertTrue(all('"Service Type" IN' in sql for sql, _ in self.executed))


class ScheduleTests(unittest.TestCase):
    """A schedule runs at 06:00 with nobody signed in; it keeps its creator's rules."""

    def test_a_schedule_runs_with_its_creators_rules(self):
        from api import report_schedules as rs
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(rs, "SCHEDULES_PATH", Path(tmp) / "s.json"), \
             mock.patch.object(rs, "_find_view", return_value={"id": "v", "title": "t", "snapshot_id": "rpt_bill_segment"}):
            s = rs.create_schedule({"saved_view_id": "v", "recipients": ["a@utility.gov"]}, organization_id="dev",
                                   created_by="u1@utility.gov", row_rules=list(WATER))
        self.assertEqual(s["row_rules"], list(WATER))
        seen = {}

        def build(**kw):
            seen.update(kw)
            return "select 1", {}
        with mock.patch("api.snapshot_catalog.snapshot_backend", return_value=("postgres", "postgres", "reporting")), \
             mock.patch("api.query_builder.build_query", side_effect=build), \
             mock.patch("api.warehouse_db.execute_query", return_value=(["m0"], [])), \
             mock.patch.object(rsec, "auth_disabled", return_value=False), \
             mock.patch.object(rsec, "_user_record",
                               return_value={"is_active": True, "role": "editor", "row_rules": list(WATER)}):
            rs.render_schedule({**s, "window_days": 30}, {"snapshot_id": "rpt_bill_segment"})
        self.assertIn({"field": "Service Type", "op": "in", "value": ["Water"]}, seen["filters"])


class AdminTests(unittest.TestCase):
    def test_a_users_rules_travel_with_them(self):
        from api.auth.models import User
        from api.auth.service import user_to_public
        u = User(id="u", email="e@x.gov", display_name="e", password_hash="x", role="editor", client_id="dev",
                 organization_id="dev", is_active=True, must_change_password=False,
                 row_rules_json='[{"field": "Service Type", "values": ["Water"]}]')
        u.group_links = []
        self.assertEqual(user_to_public(u)["row_rules"], [{"field": "Service Type", "values": ["Water"]}])


if __name__ == "__main__":
    unittest.main()


class ListingsAndMetricsTests(unittest.TestCase):
    """Everything that lists reports shows only readable ones; governed metrics carry the rule;
    alerts (which watch organization-wide cards) are refused."""

    setUp, tearDown = EnforcementTests.setUp, EnforcementTests.tearDown

    def test_the_questions_gallery_and_library_list_only_readable_canvases(self):
        from api import portal_routes as pr
        qs = se.snapshot_questions(ctx=_ctx(WATER))["questions"]
        self.assertTrue(qs)
        self.assertNotIn("rpt_rate_configuration", {q["snapshot_id"] for q in qs})
        lib = pr.report_library(ctx=self._with("report_library:read"))
        ids = {r["snapshot_id"] for p in lib["packs"] for r in p["reports"]}
        self.assertTrue(ids)
        self.assertNotIn("rpt_rate_configuration", ids)

    def _with(self, perm):
        c = _ctx(WATER)
        return AuthContext(**{**c.__dict__, "permissions": set(PERMS) | {perm}})

    def test_a_governed_metric_carries_the_rule(self):
        from api import portal_routes as pr
        with mock.patch("api.warehouse_db.warehouse_configured", return_value=True), \
             mock.patch.object(pr, "require_org_for_data", return_value="dev"):
            pr.analytics_nlq(pr.AnalyticsNlqRequest(query="billed revenue by bill cycle"), ctx=_ctx(WATER))
        self.assertTrue(self.executed)
        self.assertTrue(all('"Service Type" IN' in sql for sql, _ in self.executed))

    def test_a_governed_metric_on_an_unreadable_canvas_is_refused(self):
        from api import portal_routes as pr
        with mock.patch("api.warehouse_db.warehouse_configured", return_value=True), \
             mock.patch.object(pr, "require_org_for_data", return_value="dev"):
            with self.assertRaises(HTTPException) as err:
                pr.analytics_nlq(pr.AnalyticsNlqRequest(query="how many bills completed"), ctx=_ctx(WATER))
        self.assertEqual(err.exception.status_code, 403)

    def test_alerts_are_refused(self):
        from api import kpi_alert_routes as kr
        with mock.patch.object(kr, "require_org_for_data", return_value="dev"):
            with self.assertRaises(HTTPException) as err:
                kr.create_alert(kr.AlertCreateRequest(kpi_id="billed_revenue", condition="above", threshold=1,
                                                      recipients=["a@utility.gov"]), ctx=_ctx(WATER))
        self.assertEqual(err.exception.status_code, 403)


class CreatorsCurrentAccessTests(unittest.TestCase):
    """A schedule or embed runs with its creator's CURRENT access, not a snapshot of it:
    restricting or deactivating someone later must reach what they set up (security
    review, 2026-09-28: high)."""

    def _rules(self, record, stored=()):
        with mock.patch.object(rsec, "auth_disabled", return_value=False), \
             mock.patch.object(rsec, "_user_record", return_value=record):
            return rsec.creator_rules("u1@utility.gov", stored)

    def test_rules_added_later_apply(self):
        self.assertEqual(self._rules({"is_active": True, "role": "editor", "row_rules": list(WATER)}), WATER)

    def test_rules_lifted_later_are_lifted(self):
        self.assertEqual(self._rules({"is_active": True, "role": "editor", "row_rules": []}, stored=WATER), ())

    def test_a_deactivated_or_removed_creator_stops_it(self):
        for record in ({"is_active": False, "role": "editor", "row_rules": []}, None):
            with self.assertRaises(rsec.RowAccessDenied):
                self._rules(record)

    def test_with_sign_in_switched_off_the_stored_rules_are_used(self):
        with mock.patch.object(rsec, "auth_disabled", return_value=True):
            self.assertEqual(rsec.creator_rules("dev@origin.local", WATER), WATER)


class ScheduleWorkstreamTests(unittest.TestCase):
    """A person granted only some workstreams cannot schedule (and so mail themselves) a view
    on a canvas outside them (security review, 2026-09-28: high)."""

    def test_scheduling_a_view_outside_ones_workstreams_is_refused(self):
        from api import report_schedule_routes as rr
        billing_only = AuthContext(id="u2", email="u2@utility.gov", display_name="u2", role="editor", client_id="dev",
                                   organization_id="dev", organization_name="Dev", permissions=set(PERMS),
                                   workstreams=["billing"])
        view = {"id": "v", "title": "t", "snapshot_id": "rpt_sa_aged_balance", "visibility": "organization"}
        with mock.patch.object(rr, "require_org_for_data", return_value="dev"), \
             mock.patch.object(rr.rs, "_find_view", return_value=view):
            with self.assertRaises(HTTPException) as err:
                rr.create_schedule(rr.ScheduleCreateRequest(saved_view_id="v", recipients=["a@utility.gov"]), ctx=billing_only)
        self.assertEqual(err.exception.status_code, 403)
