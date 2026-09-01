"""Report annotations: tests written before the code.

Contract under test (api/annotations.py + api/annotation_routes.py):
  - An annotation is a short note pinned to a target (saved_view, dashboard, or
    dashboard_tile) inside one org: author, text, timestamp.
  - Creation validates target_type, non-empty text (capped), and stores author.
  - Listing is org- and target-scoped; deletion is allowed to the author or an
    admin, refused to anyone else.
  - Routes surface it all under /annotations.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.pop("PORTAL_STATE_DATABASE_URL", None)
os.environ.pop("PORTAL_AUTH_DATABASE_URL", None)

from api import annotations as an  # noqa: E402


class AnnotationStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._path = mock.patch.object(
            an, "ANNOTATIONS_PATH", Path(self._tmp.name) / "annotations.json")
        self._path.start()

    def tearDown(self):
        self._path.stop()
        self._tmp.cleanup()

    def test_create_and_list_target_scoped(self):
        note = an.create_annotation(
            {"target_type": "saved_view", "target_id": "view-1",
             "text": "Spike traced to the CYCLE3 rebill batch."},
            organization_id="dev", author_email="analyst@utility.gov")
        self.assertTrue(note["id"])
        self.assertEqual(note["author_email"], "analyst@utility.gov")
        listed = an.list_annotations("dev", target_type="saved_view", target_id="view-1")
        self.assertEqual([n["id"] for n in listed], [note["id"]])
        # other target and other org see nothing
        self.assertEqual(an.list_annotations("dev", target_type="saved_view",
                                             target_id="view-2"), [])
        self.assertEqual(an.list_annotations("ellensburg", target_type="saved_view",
                                             target_id="view-1"), [])

    def test_validation(self):
        with self.assertRaises(an.AnnotationError):
            an.create_annotation({"target_type": "sticky", "target_id": "x", "text": "hi"},
                                 organization_id="dev", author_email="a@b.gov")
        with self.assertRaises(an.AnnotationError):
            an.create_annotation({"target_type": "saved_view", "target_id": "x", "text": "  "},
                                 organization_id="dev", author_email="a@b.gov")
        with self.assertRaises(an.AnnotationError):
            an.create_annotation({"target_type": "saved_view", "target_id": "x",
                                  "text": "y" * 3000},
                                 organization_id="dev", author_email="a@b.gov")

    def test_delete_author_or_admin_only(self):
        note = an.create_annotation(
            {"target_type": "dashboard", "target_id": "d1", "text": "note"},
            organization_id="dev", author_email="analyst@utility.gov")
        # someone else, not admin -> refused
        self.assertFalse(an.delete_annotation(
            note["id"], organization_id="dev",
            requester_email="other@utility.gov", is_admin=False))
        # the author -> allowed
        self.assertTrue(an.delete_annotation(
            note["id"], organization_id="dev",
            requester_email="analyst@utility.gov", is_admin=False))
        # admin can delete anyone's
        note2 = an.create_annotation(
            {"target_type": "dashboard", "target_id": "d1", "text": "note"},
            organization_id="dev", author_email="analyst@utility.gov")
        self.assertTrue(an.delete_annotation(
            note2["id"], organization_id="dev",
            requester_email="admin@utility.gov", is_admin=True))


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.annotation_routes import router

        cls._tmp = tempfile.TemporaryDirectory()
        cls._path = mock.patch.object(
            an, "ANNOTATIONS_PATH", Path(cls._tmp.name) / "annotations.json")
        cls._path.start()
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            # dev needs a data source: require_org_for_data no longer accepts
            # the global credential fallback (audit H2).
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test",
        })
        cls._env.start()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()
        cls._path.stop()
        cls._tmp.cleanup()

    def test_crud_roundtrip(self):
        r = self.client.post("/annotations", json={
            "target_type": "saved_view", "target_id": "view-9",
            "text": "Watch this one — rebill wave inbound."})
        self.assertEqual(r.status_code, 200, r.text)
        nid = r.json()["id"]
        r = self.client.get("/annotations?target_type=saved_view&target_id=view-9")
        self.assertIn(nid, [n["id"] for n in r.json()["annotations"]])
        r = self.client.delete(f"/annotations/{nid}")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/annotations?target_type=saved_view&target_id=view-9")
        self.assertEqual(r.json()["annotations"], [])

    def test_bad_target_type_is_400(self):
        r = self.client.post("/annotations", json={
            "target_type": "nope", "target_id": "x", "text": "hi"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
