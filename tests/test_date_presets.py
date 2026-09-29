"""The server's copy of the explorer's opening date windows (api/date_presets.py) agrees with
the browser's (datePresets.ts): both suites read tests/fixtures/date_presets.json. The cache
warmer runs a large canvas's opening report over this window; if the two disagreed, the
warmed result would never be the one the page asks for."""
from __future__ import annotations

import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.date_presets import preset_range, saved_window  # noqa: E402

CASES = json.loads((ROOT / "tests" / "fixtures" / "date_presets.json").read_text())["cases"]


class DatePresetTests(unittest.TestCase):
    def test_every_shared_case(self):
        for c in CASES:
            with self.subTest(preset=c["preset"], as_of=c["as_of"]):
                self.assertEqual(preset_range(c["preset"], date.fromisoformat(c["as_of"])), c["range"])

    def test_a_saved_views_window_label_means_the_same_window(self):
        """A view saved from the explorer stores the chip's label ("Last 12 months"); an embed or
        report of that view must mean the same window, still relative to the data's end."""
        for c in CASES:
            if c.get("label"):
                with self.subTest(label=c["label"]):
                    self.assertEqual(saved_window(c["label"], None, None, date.fromisoformat(c["as_of"])), c["range"])

    def test_a_custom_range_is_fixed_and_all_dates_has_none(self):
        as_of = date(2026, 9, 28)
        self.assertEqual(saved_window("Custom range", "2026-01-01", "2026-03-31", as_of), ["2026-01-01", "2026-03-31"])
        self.assertIsNone(saved_window("All dates", "2026-01-01", "2026-03-31", as_of))
        self.assertEqual(saved_window("Last 180 days", None, None, as_of), ["2026-04-01", "2026-09-28"])
        self.assertEqual(saved_window("Last 6 months", None, None, as_of), ["2026-04-01", "2026-09-28"])
        self.assertIsNone(saved_window(None, None, None, as_of))


if __name__ == "__main__":
    unittest.main()
