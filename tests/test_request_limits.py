"""Request size and rate limits (production-readiness ledger items 7 and 8, 2026-10-05).

1. No route capped the size of what it accepted, so one request could make the API buffer and
   parse an arbitrarily large body. Anything over the cap now gets a 413 before a route runs,
   whether the body declares its length or arrives chunked.
2. The SQL workspace, explorer queries, Ori, PDF exports and the public embed route had no
   rate limit: one account (or one leaked embed link) could keep the warehouse busy. Each
   now has a per-person (per-address for the public route) sliding window and answers 429
   with a sentence and Retry-After. Per process, like the sign-in limiter: defence in depth,
   not a quota.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import request_limits  # noqa: E402
from api.app import app  # noqa: E402
from tests.test_route_guards import _routes  # noqa: E402

LIMITED = {
    ("POST", "/database/sql/execute"),
    ("POST", "/database/sql/count"),
    ("POST", "/snapshots/{snapshot_id}/raw-sql"),
    ("POST", "/snapshots/{snapshot_id}/query"),
    ("POST", "/portal/assistant"),
    ("POST", "/portal/assistant/stream"),
    ("POST", "/portal/export/pdf"),
    ("POST", "/portal/export/dashboard-pdf"),
    ("GET", "/embed/{token}/data"),
}


def _names(dependant) -> set[str]:
    out = set()
    for d in dependant.dependencies:
        out.add(getattr(d.call, "__qualname__", repr(d.call)))
        out |= _names(d)
    return out


class BodySize(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_a_body_over_the_cap_is_refused_before_any_route_runs(self):
        big = b"x" * (request_limits.MAX_BODY_BYTES + 1)
        r = self.client.post("/auth/login", content=big, headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)
        self.assertIn("too large", r.json()["detail"])

    def test_a_chunked_body_is_counted_too(self):
        chunk = b"x" * 65536
        n = request_limits.MAX_BODY_BYTES // len(chunk) + 2
        r = self.client.post("/auth/login", content=(chunk for _ in range(n)),
                             headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_an_ordinary_body_reaches_the_route(self):
        r = self.client.post("/auth/login", json={"email": "nobody@example.test", "password": "not-a-real-one"})
        self.assertNotEqual(r.status_code, 413)


class Windows(unittest.TestCase):
    def test_the_limit_holds_per_key_and_slides(self):
        w = request_limits.SlidingWindow(limit=3, seconds=60)
        clock = [1000.0]
        with mock.patch.object(request_limits, "_now", lambda: clock[0]):
            self.assertEqual([w.hit("ann") for _ in range(3)], [None, None, None])
            wait = w.hit("ann")
            self.assertIsNotNone(wait)
            self.assertGreater(wait, 0)
            self.assertIsNone(w.hit("bob"))           # another person is not slowed by ann
            clock[0] += 61
            self.assertIsNone(w.hit("ann"))           # the window slides

    def test_an_over_limit_request_reads_as_a_sentence_with_retry_after(self):
        probe = FastAPI()

        @probe.get("/probe", dependencies=[Depends(request_limits.limited("probe_test", 2, key=lambda r: "k"))])
        def _probe():
            return {"ok": True}

        client = TestClient(probe)
        codes = [client.get("/probe").status_code for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])
        over = client.get("/probe")
        self.assertIn("Retry-After", over.headers)
        self.assertIn("Wait", over.json()["detail"])


class EveryExpensiveRouteIsLimited(unittest.TestCase):
    def test_each_listed_route_carries_a_limit(self):
        found = {key: route for key, route in _routes(app) if key in LIMITED}
        self.assertEqual(set(found), LIMITED, "a listed route no longer exists")
        for key, route in found.items():
            self.assertTrue(any("limited" in n for n in _names(route.dependant)), f"{key} has no rate limit")


if __name__ == "__main__":
    unittest.main()
