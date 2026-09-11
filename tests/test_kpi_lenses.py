"""A KPI card can offer several lenses on the same question.

"Total customers · Accounts in CIS" counted EVERY account -- 562 on Demo 25.4 -- while a
reader naturally hears "customers we bill". 496 of those have at least one active service
agreement and 66 have none. Both numbers are legitimate; the card just has to say which
one it is showing, and let the reader switch.

The lens carries its own subtitle, because the subtitle is the thing that makes the
number honest: "Every account in CIS" and "No active service agreement" are different
claims about the same card.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kpi_runner import lens_filters, public_lenses, select_lens  # noqa: E402

KPI = {
    "id": "total_customers",
    "label": "Total customers",
    "subtitle": "Accounts in CIS",
    "lenses": [
        {"id": "active", "label": "Active", "subtitle": "At least one active SA",
         "filters": [{"field": "Active SA Count", "op": "gte", "value": 1}]},
        {"id": "all", "label": "All", "subtitle": "Every account", "filters": []},
        {"id": "inactive", "label": "Inactive", "subtitle": "No active SA",
         "filters": [{"field": "Active SA Count", "op": "lte", "value": 0}]},
    ],
}
PLAIN = {"id": "billed_revenue", "label": "Billed revenue", "subtitle": "Frozen FTs"}


class SelectLensTests(unittest.TestCase):
    def test_defaults_to_the_first_lens(self) -> None:
        self.assertEqual(select_lens(KPI, None)["id"], "active")

    def test_selects_by_id(self) -> None:
        self.assertEqual(select_lens(KPI, "inactive")["id"], "inactive")

    def test_an_unknown_id_falls_back_to_the_default_rather_than_erroring(self) -> None:
        # A stale link or a renamed lens must not blank the dashboard.
        self.assertEqual(select_lens(KPI, "nonsense")["id"], "active")

    def test_a_kpi_with_no_lenses_has_none(self) -> None:
        self.assertIsNone(select_lens(PLAIN, None))
        self.assertEqual(lens_filters(PLAIN, None), [])


class LensFiltersTests(unittest.TestCase):
    def test_the_chosen_lens_contributes_its_filters(self) -> None:
        self.assertEqual(
            lens_filters(KPI, "inactive"),
            [{"field": "Active SA Count", "op": "lte", "value": 0}],
        )

    def test_an_all_lens_contributes_nothing(self) -> None:
        self.assertEqual(lens_filters(KPI, "all"), [])

    def test_filters_are_copied_so_a_caller_cannot_mutate_the_spec(self) -> None:
        got = lens_filters(KPI, "active")
        got[0]["value"] = 999
        self.assertEqual(KPI["lenses"][0]["filters"][0]["value"], 1)


class PublicLensesTests(unittest.TestCase):
    def test_exposes_id_label_and_subtitle_but_never_the_filters(self) -> None:
        """Filters are server-side governance; the client only names a lens."""
        out = public_lenses(KPI)
        self.assertEqual([l["id"] for l in out], ["active", "all", "inactive"])
        for entry in out:
            self.assertEqual(set(entry), {"id", "label", "subtitle"})

    def test_a_kpi_without_lenses_exposes_an_empty_list(self) -> None:
        self.assertEqual(public_lenses(PLAIN), [])



class LensSelectionParsingTests(unittest.TestCase):
    """`?lens=<kpi_id>:<lens_id>`, repeated once per card."""

    def setUp(self):
        from api.snapshot_explorer import _lens_selection
        self.parse = _lens_selection

    def test_parses_repeated_pairs(self):
        self.assertEqual(
            self.parse(["total_customers:inactive", "active_service_agreements:all"]),
            {"total_customers": "inactive", "active_service_agreements": "all"},
        )

    def test_tolerates_whitespace(self):
        self.assertEqual(self.parse([" total_customers : all "]), {"total_customers": "all"})

    def test_drops_malformed_pairs_rather_than_raising(self):
        # A stale bookmark should render defaults, not a 400.
        self.assertEqual(self.parse(["nocolon", "", ":", "a:", ":b"]), {})

    def test_no_selection_is_an_empty_map(self):
        self.assertEqual(self.parse([]), {})


if __name__ == "__main__":
    unittest.main()


class DiscoveredLensTests(unittest.TestCase):
    """Some statuses are CLIENT-CONFIGURED and cannot be written down in advance.

    SA/bill/payment statuses are base-product `_FLG` lookups, so their lenses are named
    in the spec. A field activity's status is a business-object lifecycle state that a
    client can extend -- Demo 25.4 alone carries COMPLETED, DISCARDED, WAITEFFTDT,
    COMINPROG, VALERROR, COMERROR and WAITAPPT -- so hardcoding them would be exactly
    the "never hardcode a client-configured code" mistake. Those lenses are DISCOVERED
    from the tenant's own data, ranked by volume, through the same governed query path.
    """

    def setUp(self):
        from api import kpi_runner
        self.kpi_runner = kpi_runner
        self.kpi = {
            "id": "field_activities",
            "snapshot_id": "rpt_field_activity",
            "lens_field": {"field": "Activity Status Code", "noun": "Activity status"},
        }

    def _resolve(self, values):
        from unittest import mock
        with mock.patch.object(self.kpi_runner, "_discover_lens_values", return_value=values):
            return self.kpi_runner.resolve_lenses(self.kpi, organization_id="dev")

    def test_all_comes_first_so_it_is_the_default(self):
        out = self._resolve(["COMPLETED", "DISCARDED"])
        self.assertEqual(out["lenses"][0]["id"], "all")
        self.assertEqual(out["lenses"][0]["filters"], [])

    def test_one_lens_per_discovered_value_in_the_order_given(self):
        out = self._resolve(["COMPLETED", "DISCARDED", "WAITEFFTDT"])
        self.assertEqual(
            [l["label"] for l in out["lenses"]], ["All", "COMPLETED", "DISCARDED", "WAITEFFTDT"]
        )

    def test_each_lens_filters_on_the_declared_field_by_equality(self):
        out = self._resolve(["COMPLETED"])
        self.assertEqual(
            out["lenses"][1]["filters"],
            [{"field": "Activity Status Code", "op": "eq", "value": "COMPLETED"}],
        )

    def test_ids_are_url_safe_and_distinct(self):
        out = self._resolve(["WAIT APPT", "wait/appt", "COMPLETED"])
        ids = [l["id"] for l in out["lenses"]]
        self.assertEqual(len(ids), len(set(ids)), ids)
        for lens_id in ids:
            self.assertRegex(lens_id, r"^[a-z0-9-]+$")

    def test_a_value_that_slugs_to_nothing_still_gets_an_id(self):
        out = self._resolve(["///", "COMPLETED"])
        self.assertTrue(all(l["id"] for l in out["lenses"]))

    def test_a_spec_with_static_lenses_is_returned_untouched(self):
        static = {"id": "x", "lenses": [{"id": "a", "label": "A", "filters": []}]}
        self.assertEqual(
            self.kpi_runner.resolve_lenses(static, organization_id="dev")["lenses"],
            static["lenses"],
        )

    def test_discovery_failure_degrades_to_no_lenses_rather_than_breaking_the_card(self):
        from unittest import mock
        with mock.patch.object(
            self.kpi_runner, "_discover_lens_values", side_effect=RuntimeError("db down")
        ):
            out = self.kpi_runner.resolve_lenses(self.kpi, organization_id="dev")
        self.assertEqual(out.get("lenses", []), [])
