"""Integration test for the shared Postgres user-state store.

Runs the REAL portal_state_store against Postgres when PORTAL_STATE_DATABASE_URL
(or PORTAL_AUTH_DATABASE_URL) is set — e.g. against Supabase in CI/prod. Skips
cleanly in local dev (no DB URL), where the stores use their JSON fallback and
test_saved_views_multimeasure already covers the logic.
"""
from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import portal_state_store as pss  # noqa: E402


@unittest.skipUnless(pss.enabled(), "no PORTAL_STATE/AUTH_DATABASE_URL configured")
class PortalStateStoreTests(unittest.TestCase):
    COLLECTION = "test_collection"

    def setUp(self):
        self.org = f"test-org-{uuid.uuid4().hex[:8]}"
        self.ids: list[str] = []

    def tearDown(self):
        for rid in self.ids:
            try:
                pss.delete(self.COLLECTION, rid, self.org)
            except Exception:  # noqa: BLE001
                pass

    def _add(self, data):
        rid = str(uuid.uuid4())
        self.ids.append(rid)
        pss.upsert(self.COLLECTION, rid, self.org, {**data, "id": rid})
        return rid

    def test_roundtrip_and_scoping(self):
        rid = self._add({"title": "A", "measures": [{"field": "*", "agg": "count"}]})
        rows = pss.list_records(self.COLLECTION, self.org)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], rid)
        self.assertEqual(rows[0]["measures"][0]["agg"], "count")
        # a different org sees nothing
        self.assertEqual(pss.list_records(self.COLLECTION, "someone-else"), [])

    def test_upsert_overwrites(self):
        rid = self._add({"title": "first"})
        pss.upsert(self.COLLECTION, rid, self.org, {"id": rid, "title": "second"})
        rows = pss.list_records(self.COLLECTION, self.org)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "second")

    def test_delete(self):
        rid = self._add({"title": "x"})
        self.assertTrue(pss.delete(self.COLLECTION, rid, self.org))
        self.assertFalse(pss.delete(self.COLLECTION, rid, self.org))
        self.assertEqual(pss.list_records(self.COLLECTION, self.org), [])


if __name__ == "__main__":
    unittest.main()
