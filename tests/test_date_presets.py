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

from api.date_presets import preset_range  # noqa: E402

CASES = json.loads((ROOT / "tests" / "fixtures" / "date_presets.json").read_text())["cases"]


class DatePresetTests(unittest.TestCase):
    def test_every_shared_case(self):
        for c in CASES:
            with self.subTest(preset=c["preset"], as_of=c["as_of"]):
                self.assertEqual(preset_range(c["preset"], date.fromisoformat(c["as_of"])), c["range"])


if __name__ == "__main__":
    unittest.main()
