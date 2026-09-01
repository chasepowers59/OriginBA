"""Cross-filtering a KPI grid must not depend on CISADM's naming.

Clicking a chart value is meant to filter every tile. `_cross_filter` upper-cased the
field name -- fine when every column was CISADM's UPPER_SNAKE, wrong the moment the
canvases arrived with Title Case business names. "Customer Class" became "CUSTOMER
CLASS" and, measured on Demo 25.4, ALL NINE cards came back
`Invalid filter field: CUSTOMER CLASS` with a null value. The whole feature was dead on
the dbt path, which is every canvas-backed org and where oracle_dbt is heading too.

Case is the query builder's job -- it already upper-cases for the legacy dialect and
leaves Title Case alone for the others -- so the route must pass the field through
untouched.

The second half: a cross-filter field only exists on SOME canvases. "Customer Class" is
on the account canvas and not on the payment or aged-balance ones. Those cards must be
left unfiltered, the way any BI tool leaves an unrelated visual alone, rather than
erroring out of the grid.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kpi_runner import applicable_filters  # noqa: E402
from api.snapshot_explorer import _cross_filter  # noqa: E402


class CrossFilterFieldCaseTests(unittest.TestCase):
    def test_the_field_name_is_passed_through_untouched(self) -> None:
        self.assertEqual(
            _cross_filter("Customer Class", "Residential"),
            [{"field": "Customer Class", "op": "eq", "value": "Residential"}],
        )

    def test_a_cisadm_style_name_is_equally_untouched(self) -> None:
        # The builder upper-cases for the legacy dialect; the route must not pre-empt it.
        self.assertEqual(_cross_filter("CUST_CL_CD", "RES")[0]["field"], "CUST_CL_CD")

    def test_no_field_or_blank_value_means_no_filter(self) -> None:
        self.assertEqual(_cross_filter(None, "Residential"), [])
        self.assertEqual(_cross_filter("Customer Class", None), [])
        self.assertEqual(_cross_filter("Customer Class", "   "), [])


class ApplicableFilterTests(unittest.TestCase):
    FIELDS = {"Customer Class", "Account ID", "Active SA Count"}

    def test_keeps_a_filter_the_canvas_can_answer(self) -> None:
        f = [{"field": "Customer Class", "op": "eq", "value": "Residential"}]
        self.assertEqual(applicable_filters(f, self.FIELDS), f)

    def test_drops_one_the_canvas_has_never_heard_of(self) -> None:
        f = [{"field": "Payment Status", "op": "eq", "value": "Frozen"}]
        self.assertEqual(applicable_filters(f, self.FIELDS), [])

    def test_matches_regardless_of_case_so_either_dialect_resolves(self) -> None:
        f = [{"field": "CUSTOMER CLASS", "op": "eq", "value": "Residential"}]
        self.assertEqual(len(applicable_filters(f, self.FIELDS)), 1)

    def test_keeps_the_applicable_ones_and_drops_the_rest(self) -> None:
        f = [
            {"field": "Customer Class", "op": "eq", "value": "R"},
            {"field": "Nonexistent", "op": "eq", "value": "x"},
            {"field": "Account ID", "op": "eq", "value": "1"},
        ]
        self.assertEqual([x["field"] for x in applicable_filters(f, self.FIELDS)],
                         ["Customer Class", "Account ID"])

    def test_no_filters_stays_no_filters(self) -> None:
        self.assertEqual(applicable_filters([], self.FIELDS), [])
        self.assertEqual(applicable_filters(None, self.FIELDS), [])


if __name__ == "__main__":
    unittest.main()
