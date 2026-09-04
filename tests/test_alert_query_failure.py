"""A KPI alert whose query FAILED must not record an all-clear.

`execute_kpi_definition` never raises -- it returns `error` with `value: None`. The
alert runner ignored that field: `evaluate_condition(value=None)` returns False ("no
data never breaches", which is right), and the runner then wrote `last_state = "ok"`
and `last_status = "ok at None"`. So a query failure was recorded as an all-clear.

That is two lies. The status line in the UI says "ok at None" for an alert that could
not be evaluated. And an alert that was BREACHED flips to "ok" on the failure, so when
the query works again it NOTIFIES -- "breached-notified" -- for a condition that never
cleared. Every alert on an org whose warehouse is not built yet (five today, since all
orgs read the dbt catalog) would do exactly this, hourly.

A failed evaluation now lands in the runner's existing error branch, which records the
failure and leaves last_state alone, and the unbuilt-warehouse class reads as the same
sentence the dashboards use.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class _Store:
    def __init__(self, alerts):
        self.alerts = alerts
        self.updates = []

    def list_all(self):
        return [dict(a) for a in self.alerts]

    def update(self, alert):
        self.updates.append(dict(alert))


def _alert(last_state="breached"):
    return {"id": "a1", "kpi_id": "total_customers", "kpi_label": "Billing accounts",
            "organization_id": "newark", "condition": "above", "threshold": 10,
            "recipients": ["ops@origin.local"], "enabled": True, "last_state": last_state,
            "last_status": "notified at 12", "window_days": 7}


def _failed(error):
    return {"value": None, "pct_change": None, "error": error, "label": "Billing accounts"}


class AlertQueryFailureTests(unittest.TestCase):
    def _run(self, kpi_result, alert=None):
        import api.kpi_alerts as ka
        store = _Store([alert or _alert()])
        sent = []
        with mock.patch.object(ka, "_store", store), \
             mock.patch.object(ka, "_kpi_result", return_value=kpi_result):
            results = ka.run_kpi_alerts(send=sent.append)
        return results, store.updates, sent

    def test_a_failed_query_is_recorded_as_an_error_not_an_all_clear(self):
        results, updates, sent = self._run(_failed("Query failed: ORA-01013: user requested cancel"))
        self.assertTrue(results[0]["status"].startswith("error"), results[0]["status"])
        self.assertNotIn("ok at None", updates[-1]["last_status"])
        self.assertEqual(sent, [])

    def test_a_failed_query_does_not_move_the_breach_state(self):
        """The transition into breach is what notifies; a failure must not reset it."""
        _, updates, _ = self._run(_failed("Query failed: ORA-01013"), _alert(last_state="breached"))
        self.assertEqual(updates[-1]["last_state"], "breached")

    def test_the_unbuilt_warehouse_reads_as_the_dashboards_sentence(self):
        results, updates, _ = self._run(_failed("Query failed: ORA-00942: table or view does not exist"))
        self.assertIn("not been built", results[0]["status"].lower())
        self.assertIn("not been built", updates[-1]["last_status"].lower())
        self.assertNotIn("ORA-", updates[-1]["last_status"])

    def test_a_genuine_no_data_answer_is_still_not_a_breach(self):
        """value None with NO error is an honest empty window, and stays quiet."""
        results, updates, sent = self._run({"value": None, "pct_change": None, "error": None})
        self.assertEqual(results[0]["status"], "ok")
        self.assertEqual(sent, [])

    def test_a_working_query_still_notifies_on_the_transition(self):
        results, _, sent = self._run({"value": 42.0, "pct_change": None, "error": None},
                                     _alert(last_state="ok"))
        self.assertEqual(results[0]["status"], "breached-notified")
        self.assertEqual(len(sent), 1)


if __name__ == "__main__":
    unittest.main()
