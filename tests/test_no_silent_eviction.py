"""Saving past the limit is refused out loud; nothing a person saved is deleted to make room.

The stores kept the newest 24 views and 12 dashboards per organization and dropped the
oldest without a word (found 2026-09-28), so saving a view could delete a colleague's.
Past the limit a save now fails with a message saying what to do; the limits are higher.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import saved_dashboards as sd  # noqa: E402
from api import saved_views as sv  # noqa: E402


class NoSilentEvictionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [
            mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
            mock.patch.object(sd, "STORE_PATH", Path(self.tmp.name) / "d.json"),
            mock.patch.object(sv._pss, "enabled", return_value=False),
            mock.patch.object(sd._pss, "enabled", return_value=False),
            mock.patch.object(sv, "MAX_VIEWS", 3),
            mock.patch.object(sd, "MAX_DASHBOARDS", 2),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _view(self, n):
        return sv.create_saved_view({"snapshot_id": "rpt_bill", "snapshot_label": "Bill", "title": f"v{n}",
                                     "kind": "custom"}, organization_id="dev")

    def test_a_view_past_the_limit_is_refused_and_none_is_lost(self):
        for n in range(3):
            self._view(n)
        with self.assertRaises(sv.SavedViewError) as err:
            self._view(3)
        self.assertIn("limit", str(err.exception).lower())
        self.assertEqual(sorted(v["title"] for v in sv.list_saved_views("dev")), ["v0", "v1", "v2"])

    def test_resaving_the_same_view_replaces_it_even_at_the_limit(self):
        for n in range(3):
            self._view(n)
        self._view(1)
        self.assertEqual(len(sv.list_saved_views("dev")), 3)

    def test_a_dashboard_past_the_limit_is_refused_and_none_is_lost(self):
        for n in range(2):
            sd.create_dashboard({"title": f"d{n}", "tiles": []}, organization_id="dev")
        with self.assertRaises(sd.DashboardError):
            sd.create_dashboard({"title": "d2", "tiles": []}, organization_id="dev")
        self.assertEqual(len(sd.list_dashboards("dev")), 2)


if __name__ == "__main__":
    unittest.main()
