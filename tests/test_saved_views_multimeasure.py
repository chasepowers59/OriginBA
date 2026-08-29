"""Saved-view persistence: multi-measure round-trip + the dbt-id casing fix.

A builder view carries a measures[] array; the singular measure_field/agg stay
populated for back-compat. Snapshot ids are stored AS-WRITTEN so lowercase dbt
canvas ids (rpt_*) round-trip instead of being uppercased into a miss.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import api.saved_views as sv  # noqa: E402


class SavedViewsMultiMeasureTests(unittest.TestCase):
    def setUp(self):
        # redirect the JSON store to a temp file so the real one is untouched
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._orig = sv.VIEWS_PATH
        sv.VIEWS_PATH = Path(self._tmp.name)
        Path(self._tmp.name).write_text('{"views": []}')

    def tearDown(self):
        sv.VIEWS_PATH = self._orig
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_multimeasure_roundtrip(self):
        measures = [{"field": "*", "agg": "count"}, {"field": "Billed Amount", "agg": "sum"}]
        entry = sv.create_saved_view(
            {
                "snapshot_id": "rpt_bill_segment",
                "snapshot_label": "Bill Segment",
                "title": "Billed revenue by SA type",
                "kind": "custom",
                "dimensions": ["SA Type"],
                "measure_field": "*",
                "measure_agg": "count",
                "measures": measures,
                "chart_type": "area",
            },
            organization_id="dev",
        )
        self.assertEqual(entry["measures"], measures)
        # stored as-written (lowercase), NOT uppercased
        self.assertEqual(entry["snapshot_id"], "rpt_bill_segment")

        views = sv.list_saved_views("dev")
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]["measures"], measures)
        self.assertEqual(views[0]["chart_type"], "area")

    def test_org_scoping_isolates_views(self):
        base = {"snapshot_id": "rpt_bill", "snapshot_label": "Bill", "title": "t", "kind": "custom"}
        sv.create_saved_view(base, organization_id="dev")
        sv.create_saved_view(base, organization_id="ellensburg")
        self.assertEqual(len(sv.list_saved_views("dev")), 1)
        self.assertEqual(len(sv.list_saved_views("ellensburg")), 1)


if __name__ == "__main__":
    unittest.main()
