"""A KPI's window column must be one the rows actually carry.

Measured 2026-09-04 with pg_stats.null_frac on originba_v2_demo25 / originba_v2_int_dev_full:

    rpt_bill.Window Start Date           1.000 / 1.000   (empty on both)
    rpt_bill.Completed Date/Time         0.008 / 0.000   (null only on PENDING bills)
    rpt_field_activity.Event Date/Time   0.827 / 0.648
    rpt_field_activity.Created Date/Time 0.000 / 0.000

The Billing workstream's "Bills completed" windowed on Window Start Date and read 0
whatever the period, while the home page's "Bills" card -- deliberately moved off that
column, with the measurement in its comment -- read 1 for the same 30 days. The Field
operations workstream windowed "Field activities" on Event Date/Time and undercounted by
most of the volume the home page showed. Same-named cards disagreeing across pages is the
fastest way to lose a business reader's trust, and the executive spec's fix had not been
propagated to the workstream spec.

Two rules, pinned here so the next regen or new card cannot drift back:
  1. No card windows on a column measured empty (Window Start Date) or mostly empty
     (rpt_field_activity's Event Date/Time).
  2. A card that appears on BOTH pages for the same canvas windows on the same column,
     unless this file records why not. bills_completed is the one exception: the home
     card has Complete / Pending / All lenses, and a PENDING bill's only date is Created
     Date/Time; the workstream card counts completed bills only, so Completed Date/Time
     is the event it counts.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.executive_dashboard import EXECUTIVE_KPIS  # noqa: E402
from api.workstream_dashboard import WORKSTREAM_KPIS  # noqa: E402

MEASURED_EMPTY = {
    ("rpt_bill", "Window Start Date"),
    ("rpt_field_activity", "Event Date/Time"),
}

# (kpi id, canvas): {page: window column} -- the documented disagreements.
AGREED_DIFFERENCES = {
    ("bills_completed", "rpt_bill"): {"executive": "Created Date/Time", "workstream": "Completed Date/Time"},
}


def _workstream_kpis():
    for ws, kpis in WORKSTREAM_KPIS.items():
        for k in kpis:
            yield ws, k


class WindowFieldsAreCarriedByTheRows(unittest.TestCase):
    def test_no_card_windows_on_a_measured_empty_column(self):
        offenders = []
        for k in EXECUTIVE_KPIS:
            if (k["snapshot_id"], k.get("date_field")) in MEASURED_EMPTY:
                offenders.append(f"executive:{k['id']}")
        for ws, k in _workstream_kpis():
            if (k["snapshot_id"], k.get("date_field")) in MEASURED_EMPTY:
                offenders.append(f"{ws}:{k['id']} on {k['date_field']!r}")
        self.assertEqual(offenders, [])

    def test_a_card_on_both_pages_windows_on_the_same_column(self):
        exec_by_key = {(k["id"], k["snapshot_id"]): k.get("date_field") for k in EXECUTIVE_KPIS}
        disagreements = []
        for ws, k in _workstream_kpis():
            key = (k["id"], k["snapshot_id"])
            if key not in exec_by_key:
                continue
            e, w = exec_by_key[key], k.get("date_field")
            if key in AGREED_DIFFERENCES:
                self.assertEqual({"executive": e, "workstream": w}, AGREED_DIFFERENCES[key], key)
            elif e != w:
                disagreements.append(f"{key}: executive {e!r} vs {ws} {w!r}")
        self.assertEqual(disagreements, [])


if __name__ == "__main__":
    unittest.main()
