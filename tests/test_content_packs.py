"""Content packs: build views and dashboards once, carry them to another organization.

Jaspersoft's repository export/import is how the Standard Offering reaches each client. The
portal's equivalent: GET /portal/content-pack exports the organization-wide saved views and
dashboards (all, or one folder) as a JSON pack; POST /portal/content-pack/import (admins)
brings a pack into the organization the admin is working in.

C2M differs by client and release, so every item is checked against the TARGET
organization's catalog before it is written: a view or tile naming a canvas, column or
ready-to-run report the client does not have is skipped with the reason, never saved
broken. A dry run reports what would happen and writes nothing. Importing the same pack
twice adds nothing the second time. Private items never leave, nor anything the exporter's
workstream grants withhold from them; imported items belong to the admin who imported them
and are shared with the organization.
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

from api import content_packs as cp  # noqa: E402
from api import saved_dashboards as sd  # noqa: E402
from api import saved_views as sv  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402
from api.snapshot_catalog import CatalogError  # noqa: E402

PERMS = {"portal:read", "saved_views:write"}

# the target client's catalog: rpt_bill_segment without "Rate Schedule"; no rpt_asset
CATALOG = {
    "rpt_bill_segment": {"id": "rpt_bill_segment", "label": "Bill Segment", "workstream": "billing",
                         "fields": [{"id": f} for f in ("Bill Cycle", "Billed Amount", "Is Frozen", "SA Type")],
                         "premade_reports": [{"id": "billed_by_sa_type"}]},
    "rpt_sa_aged_balance": {"id": "rpt_sa_aged_balance", "label": "SA Aged Balance", "workstream": "debt",
                            "fields": [{"id": "Past Due Amount"}], "premade_reports": []},
}


def _snapshot(snapshot_id, organization_id=None):
    if snapshot_id not in CATALOG:
        raise CatalogError(f"Unknown snapshot: {snapshot_id}")
    return CATALOG[snapshot_id]


def _user(uid, org="dev", role="editor", workstreams=("*",)):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id=org,
                       organization_id=org, organization_name=org, permissions=set(PERMS),
                       workstreams=list(workstreams))


VIEW = {"snapshot_id": "rpt_bill_segment", "snapshot_label": "Bill Segment", "title": "Billed by cycle", "kind": "custom",
        "dimensions": ["Bill Cycle"], "measures": [{"field": "Billed Amount", "agg": "sum"}],
        "filters": [{"field": "Is Frozen", "op": "eq", "value": True}], "folder": "Billing"}
BOARD = {"title": "Billing overview", "days": 30, "folder": "Billing",
         "tiles": [{"slot": 0, "title": "By cycle", "snapshot_id": "rpt_bill_segment", "dimensions": ["Bill Cycle"],
                    "measure_field": "Billed Amount", "measure_agg": "sum"}]}


class ContentPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
                        mock.patch.object(sv._pss, "enabled", return_value=False),
                        mock.patch.object(sd, "STORE_PATH", Path(self.tmp.name) / "d.json"),
                        mock.patch.object(sd._pss, "enabled", return_value=False),
                        mock.patch.object(cp, "get_snapshot", side_effect=_snapshot),
                        mock.patch("api.auth.workstream_access.get_snapshot", side_effect=_snapshot)]
        for p in self.patches:
            p.start()
        self.ana = _user("ana")
        stamp = {"visibility": "organization", "owner_id": "ana", "owner_email": "ana@utility.gov"}
        sv.create_saved_view({**VIEW, **stamp}, organization_id="dev")
        sv.create_saved_view({**VIEW, **stamp, "title": "Mine only", "visibility": "private"}, organization_id="dev")
        sv.create_saved_view({**VIEW, **stamp, "title": "By rate", "folder": None, "dimensions": ["Rate Schedule"]},
                             organization_id="dev")
        sd.create_dashboard({**BOARD, **stamp}, organization_id="dev")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _pack(self, folder=None):
        return cp.build_pack("dev", self.ana, folder=folder)

    def test_a_pack_carries_definitions_not_identities(self):
        pack = self._pack()
        self.assertEqual(pack["format"], cp.FORMAT)
        self.assertEqual(sorted(v["title"] for v in pack["views"]), ["Billed by cycle", "By rate"])
        self.assertEqual([d["title"] for d in pack["dashboards"]], ["Billing overview"])
        for item in pack["views"] + pack["dashboards"]:
            for key in ("id", "organization_id", "client_id", "owner_id", "owner_email"):
                self.assertNotIn(key, item)
        self.assertNotIn("id", pack["dashboards"][0]["tiles"][0])

    def test_a_pack_carries_only_what_the_callers_workstreams_grant(self):
        """A billing-only editor exported the debt dashboards GET /portal/dashboards withholds."""
        stamp = {"visibility": "organization", "owner_id": "ana", "owner_email": "ana@utility.gov"}
        debt_tile = {"slot": 1, "title": "Past due", "snapshot_id": "rpt_sa_aged_balance", "dimensions": [],
                     "measure_field": "Past Due Amount", "measure_agg": "sum"}
        sd.create_dashboard({**BOARD, **stamp, "title": "Collections war room", "tiles": [{**debt_tile, "slot": 0}]},
                            organization_id="dev")
        sd.create_dashboard({**BOARD, **stamp, "title": "Mixed", "tiles": BOARD["tiles"] + [debt_tile]},
                            organization_id="dev")
        sv.create_saved_view({**VIEW, **stamp, "title": "Past due", "snapshot_id": "rpt_sa_aged_balance",
                              "dimensions": [], "measures": [{"field": "Past Due Amount", "agg": "sum"}], "filters": []},
                             organization_id="dev")
        billing = cp.build_pack("dev", _user("bob", workstreams=["billing"]))
        self.assertEqual(sorted(v["title"] for v in billing["views"]), ["Billed by cycle", "By rate"])
        self.assertEqual({d["title"]: [t["snapshot_id"] for t in d["tiles"]] for d in billing["dashboards"]},
                         {"Billing overview": ["rpt_bill_segment"], "Mixed": ["rpt_bill_segment"]})
        everything = self._pack()
        self.assertIn("Past due", [v["title"] for v in everything["views"]])
        self.assertIn("Collections war room", [d["title"] for d in everything["dashboards"]])

    def test_one_folder_can_be_exported(self):
        self.assertEqual([v["title"] for v in self._pack(folder="Billing")["views"]], ["Billed by cycle"])

    def test_import_checks_every_item_against_the_target_catalog(self):
        pack = self._pack()
        pack["views"].append({**VIEW, "title": "Assets", "snapshot_id": "rpt_asset"})
        pack["views"].append({**VIEW, "title": "Canned", "kind": "premade", "report_id": "not_here"})
        out = cp.import_pack(pack, "odessa", _user("root", org="odessa", role="admin"), dry_run=False)
        self.assertEqual(out["views"]["imported"], ["Billed by cycle"])
        reasons = {s["title"]: s["reason"] for s in out["views"]["skipped"]}
        self.assertIn("Rate Schedule", reasons["By rate"])
        self.assertIn("rpt_asset", reasons["Assets"])
        self.assertIn("not_here", reasons["Canned"])
        self.assertEqual(out["dashboards"]["imported"], ["Billing overview"])
        imported = [v for v in sv.list_saved_views("odessa")]
        self.assertEqual([(v["title"], v["owner_id"], v["visibility"], v["folder"]) for v in imported],
                         [("Billed by cycle", "root", "organization", "Billing")])

    def test_a_dry_run_writes_nothing(self):
        out = cp.import_pack(self._pack(), "odessa", _user("root", org="odessa", role="admin"), dry_run=True)
        self.assertEqual(out["views"]["imported"], ["Billed by cycle"])
        self.assertEqual(sv.list_saved_views("odessa"), [])
        self.assertEqual(sd.list_dashboards("odessa"), [])

    def test_importing_twice_adds_nothing_the_second_time(self):
        root = _user("root", org="odessa", role="admin")
        cp.import_pack(self._pack(), "odessa", root, dry_run=False)
        again = cp.import_pack(self._pack(), "odessa", root, dry_run=False)
        self.assertEqual(again["views"]["imported"], [])
        self.assertIn("already", {s["title"]: s["reason"] for s in again["views"]["skipped"]}["Billed by cycle"])
        self.assertEqual(len(sv.list_saved_views("odessa")), 1)
        self.assertEqual(len(sd.list_dashboards("odessa")), 1)

    def test_a_tile_on_a_missing_column_skips_its_dashboard(self):
        pack = self._pack()
        pack["dashboards"][0]["tiles"][0]["dimensions"] = ["Rate Schedule"]
        out = cp.import_pack(pack, "odessa", _user("root", org="odessa", role="admin"), dry_run=False)
        self.assertEqual(out["dashboards"]["imported"], [])
        self.assertIn("By cycle", out["dashboards"]["skipped"][0]["reason"])

    def test_something_that_is_not_a_pack_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            cp.import_pack({"views": []}, "odessa", _user("root", org="odessa", role="admin"), dry_run=True)
        self.assertEqual(err.exception.status_code, 400)


class RouteTests(unittest.TestCase):
    def test_only_an_admin_imports(self):
        from api import content_pack_routes as cr
        with self.assertRaises(HTTPException) as err:
            cr.import_content_pack(cr.ImportRequest(pack={"format": cp.FORMAT, "views": [], "dashboards": []}),
                                   dry_run=True, ctx=_user("ana"))
        self.assertEqual(err.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
