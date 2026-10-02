"""A conversation belongs to the organization it was had in (2026-10-02).
The browser keeps Ori's thread in session storage so it follows the reader between pages,
and the organization switch is a full reload that storage survives: the Ellensburg thread
(a cancelled-tender table) showed under CityCorp's banner, and a follow-up would have sent
Ellensburg's figures into CityCorp's model context. The client now keeps conversations per
organization; the server stamps every thread it hands back and drops one sent back under
another organization, so no client can mix two tenants' threads.
"""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import assistant_routes  # noqa: E402


class ThreadScopeTests(unittest.TestCase):
    def test_a_thread_is_kept_only_for_the_organization_it_was_stamped_with(self):
        thread = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "x"}]
        self.assertEqual(assistant_routes.scoped_thread(thread, "ellensburg", "ellensburg"), thread)
        self.assertEqual(assistant_routes.scoped_thread(thread, "ellensburg", "citycorp"), [])
        self.assertEqual(assistant_routes.scoped_thread(thread, None, "citycorp"), [])     # unstamped: not trusted
        self.assertEqual(assistant_routes.scoped_thread([], None, "citycorp"), [])

    def test_both_asks_scope_the_thread_and_stamp_the_answer(self):
        for name in ("ask", "ask_streaming"):
            with self.subTest(route=name):
                src = inspect.getsource(getattr(assistant_routes, name))
                self.assertIn("scoped_thread(", src)
                self.assertIn("thread_organization", src)


if __name__ == "__main__":
    unittest.main()
