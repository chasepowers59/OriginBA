"""The medium and low findings of the 2026-09-28 security review, each pinned.

- Send now re-checks the workstream grant on the schedule's view, like creating one does.
- KPI alerts watch organization-wide cards: a person limited to part of the data sees none
  of them (their last values are organization-wide), and only an alert's creator or an
  administrator removes it.
- Data checks (integrity) list only canvases the person's workstreams reach; the detail of
  one they cannot reach is refused; a restricted person sees the verdict, not the
  organization-wide figures behind it. The assistant's verification tool keeps to the same
  readable canvases as every other tool.
- Notes on a saved view or dashboard follow the item's visibility: another person's private
  item is "not found".
- Imported views get an owner like any saved view.
- An Excel cell that starts with "=" is text, never a formula.
- Declining to list a large column's values does not state the table's size.
- The legacy /nlq route (no organization, no row rules) is gone from the portal API.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth.dependencies import AuthContext  # noqa: E402

PERMS = {"portal:read", "saved_views:write", "snapshots:query"}
WATER = ({"field": "Service Type", "values": ["Water"]},)


def _user(uid, role="editor", rules=(), workstreams=("*",)):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions=set(PERMS),
                       workstreams=list(workstreams), row_rules=tuple(rules))


class SendNowTests(unittest.TestCase):
    def test_send_now_rechecks_the_workstream_grant(self):
        from api import report_schedule_routes as rr
        schedule = {"id": "s1", "saved_view_id": "v1", "created_by": "ana@utility.gov", "recipients": ["x@y.z"]}
        view = {"id": "v1", "snapshot_id": "rpt_payment", "visibility": "organization"}
        denied = HTTPException(status_code=403, detail="no grant")
        with mock.patch.object(rr, "require_org_for_data", return_value="dev"), \
             mock.patch.object(rr.rs, "list_schedules", return_value=[schedule]), \
             mock.patch.object(rr.rs, "_find_view", return_value=view), \
             mock.patch.object(rr, "list_saved_views", return_value=[view]), \
             mock.patch.object(rr, "smtp_configured", return_value=True), \
             mock.patch.object(rr, "assert_snapshot_access", side_effect=denied) as check, \
             mock.patch.object(rr.rs, "deliver") as deliver:
            with self.assertRaises(HTTPException) as err:
                rr.run_now("s1", ctx=_user("ana"))
        self.assertEqual(err.exception.status_code, 403)
        check.assert_called_once()
        self.assertEqual(check.call_args.args[1], "rpt_payment")
        deliver.assert_not_called()


class AlertTests(unittest.TestCase):
    def setUp(self):
        from api import kpi_alert_routes as kr
        from api import kpi_alerts as ka
        self.kr, self.ka = kr, ka
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(ka, "ALERTS_PATH", Path(self.tmp.name) / "a.json"),
                        mock.patch.object(kr, "require_org_for_data", return_value="dev")]
        for p in self.patches:
            p.start()
        kpi = ka.watchable_kpis()[0]["id"]
        self.alert = kr.create_alert(kr.AlertCreateRequest(kpi_id=kpi, condition="above", threshold=1,
                                                           recipients=["ana@utility.gov"]), ctx=_user("ana"))

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_a_restricted_person_sees_no_alerts(self):
        self.assertEqual(len(self.kr.get_alerts(ctx=_user("bob"))["alerts"]), 1)
        self.assertEqual(self.kr.get_alerts(ctx=_user("bob", rules=WATER))["alerts"], [])

    def test_only_the_creator_or_an_admin_removes_an_alert(self):
        with self.assertRaises(HTTPException) as err:
            self.kr.delete_alert(self.alert["id"], ctx=_user("bob"))
        self.assertEqual(err.exception.status_code, 403)
        self.assertEqual(self.kr.delete_alert(self.alert["id"], ctx=_user("root", role="admin"))["deleted"],
                         self.alert["id"])


OVERVIEW = {"available": True, "canvases": [{"canvas": "rpt_bill_segment", "verdict": "proven"},
                                            {"canvas": "rpt_payment", "verdict": "differences"}]}
DETAIL = {"canvas": "rpt_payment", "available": True, "verdict": "differences", "canvas_as_of": "2026-09-27",
          "canvas_age_hours": 20,
          "source": {"run_at": "t", "checks": 3, "green": 2,
                     "differences": [{"check": "total", "warehouse": 1234567.5, "source": 1234000.0}]},
          "snapshot": {"run_at": "t", "against": "FT_RPT_CURR", "compared": 480000, "newer": 3, "missing": 0,
                       "strict_mismatches": 0, "soft_differences": [], "ok": True, "others": []}}


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        from api import integrity_routes as ir
        self.ir = ir
        self.patches = [mock.patch.object(ir, "require_org_for_data", return_value="dev"),
                        mock.patch.object(ir, "overview", return_value=OVERVIEW),
                        mock.patch.object(ir, "canvas_summary", return_value=DETAIL),
                        mock.patch("api.auth.workstream_access.can_access_snapshot",
                                   side_effect=lambda ctx, s: s == "rpt_payment")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_the_overview_lists_only_granted_canvases(self):
        out = self.ir.integrity_overview(ctx=_user("ana"))
        self.assertEqual([c["canvas"] for c in out["canvases"]], ["rpt_payment"])

    def test_an_ungranted_canvas_detail_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            self.ir.integrity_canvas("rpt_bill_segment", ctx=_user("ana"))
        self.assertEqual(err.exception.status_code, 403)

    def test_a_restricted_person_gets_the_verdict_without_the_figures(self):
        out = self.ir.integrity_canvas("rpt_payment", ctx=_user("ana", rules=WATER))
        self.assertEqual(out["verdict"], "differences")
        self.assertNotIn("1234567", repr(out))
        self.assertNotIn("480000", repr(out))
        self.assertEqual(self.ir.integrity_canvas("rpt_payment", ctx=_user("ana")), DETAIL)

    def test_the_assistant_verification_tool_keeps_to_readable_canvases(self):
        from api import assistant
        token = assistant._CAN_READ.set(lambda c: c != "rpt_payment")
        try:
            with mock.patch.object(assistant, "canvas_summary", return_value=DETAIL):
                self.assertIn("error", assistant.tool_verification_status("dev", "rpt_payment"))
        finally:
            assistant._CAN_READ.reset(token)


class AnnotationAndImportTests(unittest.TestCase):
    def setUp(self):
        from api import annotations as an
        from api import portal_routes as pr
        from api import saved_views as sv
        self.pr = pr
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
                        mock.patch.object(sv._pss, "enabled", return_value=False),
                        mock.patch.object(an, "ANNOTATIONS_PATH", Path(self.tmp.name) / "n.json"),
                        mock.patch("api.annotation_routes.require_org_for_data", return_value="dev")]
        for p in self.patches:
            p.start()
        self.private = pr.post_saved_view(pr.SavedViewCreate(snapshot_id="rpt_bill_segment", snapshot_label="Bill",
                                                             title="mine", kind="custom", visibility="private"),
                                          ctx=_user("ana"))

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_notes_on_another_persons_private_view_are_not_found(self):
        from api import annotation_routes as ar
        body = ar.AnnotationCreateRequest(target_type="saved_view", target_id=self.private["id"], text="hi")
        self.assertTrue(ar.create_annotation(body, ctx=_user("ana")))
        for call in (lambda: ar.create_annotation(body, ctx=_user("bob")),
                     lambda: ar.get_annotations("saved_view", self.private["id"], ctx=_user("bob")),
                     lambda: ar.get_annotations("saved_view", "no-such-view", ctx=_user("ana"))):
            with self.assertRaises(HTTPException) as err:
                call()
            self.assertEqual(err.exception.status_code, 404)

    def test_imported_views_have_an_owner(self):
        out = self.pr.import_saved_views(self.pr.SavedViewBulkImport(views=[self.pr.SavedViewCreate(
            snapshot_id="rpt_bill_segment", snapshot_label="Bill", title="imported", kind="custom",
            visibility="private")]), ctx=_user("bob"))
        self.assertEqual(out["views"][0]["owner_id"], "bob")


class ExportTests(unittest.TestCase):
    def test_an_excel_cell_that_looks_like_a_formula_is_text(self):
        from openpyxl import load_workbook

        from api.report_schedules import rows_to_xlsx
        data = rows_to_xlsx(["Name"], {}, [{"Name": '=HYPERLINK("http://x.test","click")'}])
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
            f.write(data)
            f.flush()
            cell = load_workbook(f.name).active["A2"]
        self.assertEqual(cell.data_type, "s")
        self.assertEqual(cell.value, '=HYPERLINK("http://x.test","click")')

    def test_declining_a_large_column_does_not_state_the_table_size(self):
        from api import snapshot_explorer as se
        snapshot = {"id": "rpt_payment", "fields": [{"id": "Bill Cycle", "role": "dimension"}], "scope_filters": []}
        with mock.patch.object(se, "require_org_for_data", return_value="dev"), \
             mock.patch.object(se, "_require_snapshot_access", return_value=snapshot), \
             mock.patch.object(se, "allowed_fields", return_value={"Bill Cycle"}), \
             mock.patch.object(se, "_row_estimate", return_value=5_123_456):
            out = se.snapshot_scope_options("rpt_payment", "Bill Cycle", where=None, ctx=_user("ana"))
        self.assertFalse(out["enumerable"])
        self.assertNotRegex(out["reason"], r"\d")


class LegacyNlqTests(unittest.TestCase):
    def test_the_portal_api_has_no_legacy_nlq_route(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "test"}):
            from api.app import app
        self.assertNotIn("/nlq", {getattr(r, "path", "") for r in app.routes})


if __name__ == "__main__":
    unittest.main()
