"""Concurrent requests for the same cold result build it once.

Review 2026-09-29: the cache did not coordinate concurrent misses. The data-quality rules take 4
of an organization's 8 Oracle sessions and Ori's history 5, so two people opening the same cold
page (or the warmer plus one person) held every session and the organization's other pages
waited. The second caller for a key now waits for the first build; different keys still build
side by side.
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import summary_cache as sc  # noqa: E402


class SingleFlightTests(unittest.TestCase):
    def setUp(self):
        sc.clear()

    def test_the_same_key_is_built_once(self):
        builds = []

        def build():
            builds.append(1)
            time.sleep(0.3)
            return {"kpis": []}
        results = []
        threads = [threading.Thread(target=lambda: results.append(sc.cached(("dq", "ellensburg"), build, version="v")))
                   for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(builds), 1)
        self.assertEqual(results, [{"kpis": []}] * 4)

    def test_different_keys_build_side_by_side(self):
        both = threading.Barrier(2, timeout=5)

        def build():
            both.wait()   # raises BrokenBarrierError if the other key's build cannot start meanwhile
            return {"kpis": []}
        errors = []

        def run(key):
            try:
                sc.cached(key, build, version="v")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
        threads = [threading.Thread(target=run, args=((k,),)) for k in ("a", "b")]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
