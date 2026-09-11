"""A scheduled report on an unbuilt warehouse records a sentence, and sends nothing.

The runner already does the important half right: render_schedule raises, the except
branch catches it, nothing is mailed. But last_status then read
"error: ORA-00942: table or view does not exist", and ScheduleDialog renders that
string next to the schedule. Every org reads the dbt catalog now, so on an org whose
in-database warehouse is not built yet that is what every schedule showed, hourly.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _Store:
    def __init__(self, rows):
        self.rows, self.updates = rows, []

    def list_all(self):
        return [dict(r) for r in self.rows]

    def update(self, row):
        self.updates.append(dict(row))


def _schedule():
    return {"id": "s1", "saved_view_id": "v1", "organization_id": "newark",
            "view_title": "Aged debt", "recipients": ["ops@origin.local"],
            "cadence": "daily", "hour_utc": 9, "enabled": True, "last_run_at": None,
            "last_status": None, "window_days": 30}


class ScheduleOnUnbuiltWarehouseTests(unittest.TestCase):
    def _run(self, exc):
        import api.report_schedules as rs
        store = _Store([_schedule()]); sent = []
        with mock.patch.object(rs, "_store", store), \
             mock.patch.object(rs, "_find_view", return_value={"snapshot_id": "rpt_bill"}), \
             mock.patch.object(rs, "render_schedule", side_effect=exc):
            results = rs.run_due_schedules(now=datetime(2026, 9, 2, 12, tzinfo=timezone.utc),
                                           send=sent.append)
        return results, store.updates, sent

    def test_nothing_is_mailed_and_the_status_is_a_sentence(self):
        results, updates, sent = self._run(RuntimeError('relation "reporting.rpt_bill" does not exist'))
        self.assertEqual(sent, [])
        self.assertIn("not been built", results[0]["status"].lower())
        self.assertIn("not been built", updates[-1]["last_status"].lower())
        self.assertNotIn("relation", updates[-1]["last_status"])

    def test_any_other_failure_still_says_what_happened(self):
        results, updates, sent = self._run(RuntimeError("SMTP refused"))
        self.assertEqual(sent, [])
        self.assertIn("SMTP refused", updates[-1]["last_status"])


class MidnightScheduleTests(unittest.TestCase):
    """hour_utc=0 is a real hour. `int(x or 13)` turned it into 13 on both the due check
    and at creation, so a schedule set for midnight UTC silently ran at 13:00 -- found
    when a test fixture with hour_utc=0 was never due at noon."""

    def test_a_midnight_schedule_is_due_just_after_midnight(self):
        from api.report_schedules import is_due
        s = {**_schedule(), "hour_utc": 0}
        self.assertTrue(is_due(s, datetime(2026, 9, 2, 0, 30, tzinfo=timezone.utc)))

    def test_and_is_not_still_waiting_for_one_pm(self):
        from api.report_schedules import is_due
        s = {**_schedule(), "hour_utc": 0}
        # at 12:59 it must ALREADY have been due for thirteen hours, not "not yet"
        self.assertTrue(is_due(s, datetime(2026, 9, 2, 12, 59, tzinfo=timezone.utc)))

    def test_creation_keeps_zero_as_zero(self):
        import api.report_schedules as rs
        store = _Store([])
        with mock.patch.object(rs, "_store", store), \
             mock.patch.object(rs, "_find_view", return_value={"title": "v", "snapshot_id": "rpt_bill"}), \
             mock.patch.object(rs, "list_schedules", return_value=[]), \
             mock.patch.object(store, "add", lambda row: row, create=True):
            created = rs.create_schedule(
                {"saved_view_id": "v1", "recipients": ["ops@origin.local"], "cadence": "daily",
                 "hour_utc": 0}, organization_id="newark", created_by="t")
        self.assertEqual(created["hour_utc"], 0)


if __name__ == "__main__":
    unittest.main()
