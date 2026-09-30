"""A busy warehouse pool makes a borrower wait; it never fails the card.

psycopg2's ThreadedConnectionPool raises "connection pool exhausted" the moment every
connection is lent out. The home page fans out 8 KPI queries per request, so two people
opening it together (or the crawl's two workers, 2026-09-28) put "Query failed:
connection pool exhausted" on cards that would have loaded a second later.
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import warehouse_db  # noqa: E402


class FakePool:
    """Behaves like psycopg2's pool: raises when every connection is lent out."""

    def __init__(self, minconn, maxconn, dsn=None):
        self.max, self.out, self.lock, self.built = maxconn, 0, threading.Lock(), 1

    def getconn(self):
        with self.lock:
            if self.out >= self.max:
                raise RuntimeError("connection pool exhausted")
            self.out += 1
        return mock.MagicMock()

    def putconn(self, conn):
        with self.lock:
            self.out -= 1


class PoolTests(unittest.TestCase):
    def setUp(self):
        warehouse_db._pools.clear()
        self.patches = [
            mock.patch.object(warehouse_db, "warehouse_url", return_value="postgresql://fake/db"),
            mock.patch.object(warehouse_db, "_pool_max", return_value=4),
            mock.patch("psycopg2.pool.ThreadedConnectionPool", FakePool),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        warehouse_db._pools.clear()

    def _borrow(self, errors):
        try:
            with warehouse_db.warehouse_connection("demo25"):
                time.sleep(0.05)
        except Exception as exc:  # noqa: BLE001
            errors.append(str(exc))

    def test_more_borrowers_than_connections_all_succeed(self):
        errors: list[str] = []
        threads = [threading.Thread(target=self._borrow, args=(errors,)) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])

    def test_one_pool_per_database_even_when_first_use_is_concurrent(self):
        built = []
        real = FakePool.__init__

        def counting(self, *a, **k):
            built.append(1)
            time.sleep(0.02)
            real(self, *a, **k)

        with mock.patch.object(FakePool, "__init__", counting):
            threads = [threading.Thread(target=warehouse_db._pool, args=("demo25",)) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual(len(built), 1)


if __name__ == "__main__":
    unittest.main()
