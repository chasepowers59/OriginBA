"""The filter value picker must not scan a fact table to fill a dropdown.

`/snapshots/{id}/scope-options/{field}` runs SELECT DISTINCT over the canvas. That is
fine on a dimension and ruinous on a fact, and the catalog declares NO scope_filters,
so the picker is offered on any of 1,107 dimension columns across the canvases.
Measured on originba_v2_demo25:

    reporting.rpt_billed_charge     46,661 rows ->  42 ms
    reporting.rpt_batch            748,848 rows -> 139 ms
    reporting.rpt_measurement    3,565,096 rows -> 608 ms

Roughly linear, so Newark and College Station (~35M FTs) land near six seconds for a
dropdown. Indexing every one of the 1,107 columns is not an option, and sampling the
table would quietly change what the list MEANS -- a picker that silently shows some of
the values is the same class of bug as a message describing a scope the query did not
apply.

So the API declines instead: above the threshold it returns `enumerable: false` with a
reason, and the component falls back to the free-text input it already had for the
"list unavailable" case. Declining is honest and instant; the user types the value and
the filter works exactly as before.

The estimate comes from table statistics, which cost nothing to read and which the
reporting layer now maintains (dbt_project.yml runs ANALYZE as a post-hook).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.snapshot_explorer import (  # noqa: E402
    SCOPE_ENUMERATION_MAX_ROWS,
    can_enumerate_values,
)


class CanEnumerateValuesTests(unittest.TestCase):
    def test_a_dimension_sized_table_still_gets_a_picker(self):
        self.assertTrue(can_enumerate_values(46_661))     # 42 ms measured
        self.assertTrue(can_enumerate_values(748_848))    # 139 ms measured

    def test_a_fact_sized_table_does_not(self):
        self.assertFalse(can_enumerate_values(3_565_096))  # 608 ms measured
        self.assertFalse(can_enumerate_values(35_800_000))  # College Station

    def test_the_threshold_is_inclusive_and_deliberate(self):
        self.assertTrue(can_enumerate_values(SCOPE_ENUMERATION_MAX_ROWS))
        self.assertFalse(can_enumerate_values(SCOPE_ENUMERATION_MAX_ROWS + 1))

    def test_an_unknown_estimate_is_attempted_rather_than_refused(self):
        """A table nothing has analyzed reports no estimate. Attempting preserves the
        behaviour that shipped; refusing would break every picker on a fresh database
        before the first ANALYZE lands."""
        self.assertTrue(can_enumerate_values(None))
        self.assertTrue(can_enumerate_values(-1))   # Postgres reltuples before ANALYZE
        self.assertTrue(can_enumerate_values(0))

    def test_a_nonsense_estimate_does_not_crash_the_picker(self):
        self.assertTrue(can_enumerate_values("not a number"))


class ThresholdTests(unittest.TestCase):
    def test_the_threshold_sits_where_the_measurements_put_it(self):
        # Between rpt_batch (139 ms, keeps its picker) and rpt_measurement (608 ms,
        # loses it). Moving it is a latency decision, so it should be a visible edit.
        self.assertGreater(SCOPE_ENUMERATION_MAX_ROWS, 748_848)
        self.assertLess(SCOPE_ENUMERATION_MAX_ROWS, 3_565_096)


if __name__ == "__main__":
    unittest.main()
