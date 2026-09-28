"""Saved views and dashboards have an owner, and can be private.

Before 2026-09-28 every view and dashboard was visible to the whole organization and any
writer could delete anyone's (the Jaspersoft-parity inventory). Now each carries its
owner and a visibility: 'organization' (the default, as before) or 'private'. A private
item is listed only for its owner; only the owner or an admin may change or delete an
item; items saved before owners existed stay editable by any writer so nothing in use
breaks. Every item says whether the caller may edit it (`can_edit`), so the UI offers
only what will work.
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

from api import portal_routes as pr  # noqa: E402
from api import saved_dashboards as sd  # noqa: E402
from api import saved_views as sv  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

WRITE = {"portal:read", "saved_views:write", "dashboards:write"}


def _user(uid, role="editor"):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions=set(WRITE), workstreams=["*"])


ALICE, BOB, ADMIN = _user("alice"), _user("bob"), _user("root", role="admin")


class _Stores(unittest.TestCase):
    """Temporary stores and helpers; no tests of its own."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
            mock.patch.object(sd, "STORE_PATH", Path(self.tmp.name) / "d.json"),
            mock.patch.object(sv._pss, "enabled", return_value=False),
            mock.patch.object(sd._pss, "enabled", return_value=False),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _view(self, who, title, visibility="organization"):
        return pr.post_saved_view(pr.SavedViewCreate(snapshot_id="rpt_bill", snapshot_label="Bill", title=title,
                                                     kind="custom", visibility=visibility), ctx=who)


class OwnershipTests(_Stores):

    def _titles(self, who):
        return sorted(v["title"] for v in pr.get_saved_views(ctx=who)["views"])

    def test_a_private_view_is_listed_only_for_its_owner(self):
        self._view(ALICE, "mine", "private")
        self._view(ALICE, "shared")
        self.assertEqual(self._titles(ALICE), ["mine", "shared"])
        self.assertEqual(self._titles(BOB), ["shared"])
        self.assertEqual(self._titles(ADMIN), ["shared"], "private means private, admins included")

    def test_only_the_owner_or_an_admin_deletes_a_view(self):
        shared = self._view(ALICE, "shared")
        with self.assertRaises(HTTPException) as err:
            pr.remove_saved_view(shared["id"], ctx=BOB)
        self.assertEqual(err.exception.status_code, 403)
        pr.remove_saved_view(shared["id"], ctx=ADMIN)
        self.assertEqual(self._titles(ALICE), [])

    def test_each_view_says_whether_the_caller_may_edit_it(self):
        self._view(ALICE, "shared")
        self.assertTrue(pr.get_saved_views(ctx=ALICE)["views"][0]["can_edit"])
        self.assertFalse(pr.get_saved_views(ctx=BOB)["views"][0]["can_edit"])

    def test_a_view_saved_before_owners_existed_stays_editable(self):
        legacy = sv.create_saved_view({"snapshot_id": "rpt_bill", "snapshot_label": "Bill", "title": "old",
                                       "kind": "custom"}, organization_id="dev")
        self.assertTrue(pr.get_saved_views(ctx=BOB)["views"][0]["can_edit"])
        pr.remove_saved_view(legacy["id"], ctx=BOB)

    def test_an_unknown_visibility_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            self._view(ALICE, "x", "everyone")
        self.assertEqual(err.exception.status_code, 400)

    def _board(self, who, title, visibility="organization"):
        return pr.post_dashboard(pr.DashboardCreate(title=title, tiles=[], visibility=visibility), ctx=who)

    def test_a_private_dashboard_is_invisible_to_others(self):
        board = self._board(ALICE, "mine", "private")
        self.assertEqual([d["title"] for d in pr.get_dashboards(ctx=BOB)["dashboards"]], [])
        with self.assertRaises(HTTPException) as err:
            pr.get_dashboard_by_id(board["id"], ctx=BOB)
        self.assertEqual(err.exception.status_code, 404)
        self.assertEqual(pr.get_dashboard_by_id(board["id"], ctx=ALICE)["title"], "mine")

    def test_only_the_owner_or_an_admin_changes_or_deletes_a_dashboard(self):
        board = self._board(ALICE, "shared")
        for attempt in (lambda: pr.put_dashboard(board["id"], pr.DashboardUpdate(title="hijacked"), ctx=BOB),
                        lambda: pr.remove_dashboard(board["id"], ctx=BOB)):
            with self.assertRaises(HTTPException) as err:
                attempt()
            self.assertEqual(err.exception.status_code, 403)
        self.assertEqual(pr.put_dashboard(board["id"], pr.DashboardUpdate(title="renamed"), ctx=ALICE)["title"], "renamed")
        pr.remove_dashboard(board["id"], ctx=ADMIN)


if __name__ == "__main__":
    unittest.main()


class ScheduleOwnershipTests(_Stores):
    """A schedule follows its view: nobody schedules a view they cannot see, a private view's
    schedules are listed only for its owner, and a schedule is removed only by its creator
    or an admin."""

    def setUp(self):
        super().setUp()
        from api import report_schedules as rs
        self.rs = rs
        self.more = [mock.patch.object(rs, "SCHEDULES_PATH", Path(self.tmp.name) / "s.json")]
        for p in self.more:
            p.start()

    def tearDown(self):
        for p in self.more:
            p.stop()
        super().tearDown()

    def _schedule(self, who, view_id):
        from api import report_schedule_routes as rr
        return rr.create_schedule(rr.ScheduleCreateRequest(saved_view_id=view_id, recipients=["a@utility.gov"]), ctx=who)

    def _listed(self, who):
        from api import report_schedule_routes as rr
        return [s["id"] for s in rr.get_schedules(ctx=who)["schedules"]]

    def test_nobody_schedules_a_view_they_cannot_see(self):
        private = self._view(ALICE, "mine", "private")
        with self.assertRaises(HTTPException) as err:
            self._schedule(BOB, private["id"])
        self.assertEqual(err.exception.status_code, 404)

    def test_a_private_views_schedules_are_listed_only_for_its_owner(self):
        private = self._view(ALICE, "mine", "private")
        sched = self._schedule(ALICE, private["id"])
        self.assertIn(sched["id"], self._listed(ALICE))
        self.assertNotIn(sched["id"], self._listed(BOB))

    def test_only_the_creator_or_an_admin_removes_a_schedule(self):
        from api import report_schedule_routes as rr
        shared = self._view(ALICE, "shared")
        sched = self._schedule(ALICE, shared["id"])
        with self.assertRaises(HTTPException) as err:
            rr.delete_schedule(sched["id"], ctx=BOB)
        self.assertEqual(err.exception.status_code, 403)
        rr.delete_schedule(sched["id"], ctx=ADMIN)
