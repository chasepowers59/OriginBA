"""Every workstream the catalog lists has KPI cards.

Asset Operations and Operations & Shared Services had none: the summary route
returned 404 and the page showed "Click spark chart bars to cross-filter all tiles"
over nothing (2026-09-04). A workstream a business reader can navigate to is a
workstream with a dashboard.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402


class EveryWorkstreamHasCards(unittest.TestCase):
    def test_catalog_workstreams_all_have_kpis(self):
        order = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["workstream_order"]
        missing = [w for w in order if not WORKSTREAM_KPIS.get(w)]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
