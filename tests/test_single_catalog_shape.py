"""There is ONE catalog shape. The legacy CISADM snapshot catalog is retired.

Until 2026-09-02 the portal served two shapes: the dbt reporting layer (Title Case
canvases, `rpt_*`) and the legacy `*_RPT_CURR` snapshots read straight out of CISADM
(`catalog: cisadm`). Six of the seven client orgs were on the legacy one, and the dev
org was not — so every shape-specific read was written against the shape that could
not reveal the bug. In ONE session that root cause produced six distinct defects:

    required_date_field read alone    19 canvases silently windowed, 38 unbounded
    required_date_label ignored       raw ACCOUNTING_DT shown to six orgs
    prettifyFieldName                 "ACCOUNTING Date" for the shape it was written for
    measureIsCurrency                 46 of 47 money measures lost their dollar sign
    snapshot_workstream               authz against the WRONG catalog; six orgs locked out
    assert_no_micr_downstream         "Alert Info" passed the test that exists to stop it

Every one of those is impossible once there is one shape. So the legacy catalog, the
legacy `oracle` dialect, `is_warehouse`, `validate_oracle_cisadm_scope` and the entire
`required_date_field` concept are removed rather than left as dormant branches — a
dormant branch is exactly where the next shape-specific bug goes to hide.

WHAT STAYS: CISADM the SCHEMA. The SQL workspace exists so analysts can query the
schema they know, and `validate_oracle_reporting_scope` fences CISADM + the reporting
layer. Retiring the *snapshot catalog* is not retiring the schema.

WHAT IS NOT DONE HERE, deliberately: no dbt build on the other five clients and no QA
of their data. Pointing an org at `catalog: dbt` makes the portal READY for the
in-database warehouse to be built there, exactly as Ellensburg's was; it does not
build it. An org so pointed, before its build, will serve empty canvases — which is
honest, and which `db-health`-style row counts will show, rather than a silently wrong
legacy number.

Some checks below read source as TEXT. That is the trap recorded in
test_modules_load.py, and it is used on purpose here: the requirement is literally that
the legacy shape is no longer MENTIONED in the app, and a mention is a text property.
Every behavioural claim is tested behaviourally alongside.
"""

from __future__ import annotations

import inspect
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _orgs() -> list[dict]:
    raw = json.loads((ROOT / "config" / "portal_organizations.json").read_text())
    return raw.get("organizations", raw) if isinstance(raw, dict) else raw


class OneCatalogTests(unittest.TestCase):
    def test_every_organization_reads_the_dbt_catalog(self):
        for org in _orgs():
            self.assertEqual(org.get("catalog"), "dbt", org["id"])

    def test_the_loader_knows_exactly_one_catalog(self):
        from api.snapshot_catalog import CATALOGS
        self.assertEqual(set(CATALOGS), {"dbt"})

    def test_the_legacy_catalog_file_is_gone(self):
        self.assertFalse((ROOT / "output" / "catalog_cisadm.json").exists(),
                         "output/catalog_cisadm.json must be deleted, not just unrouted")

    def test_no_org_can_resolve_to_a_second_catalog(self):
        from api.snapshot_catalog import catalog_name_for_org
        for org in _orgs():
            self.assertEqual(catalog_name_for_org(org["id"]), "dbt", org["id"])
        self.assertEqual(catalog_name_for_org(None), "dbt")
        self.assertEqual(catalog_name_for_org("no-such-org"), "dbt")

    def test_no_snapshot_is_a_legacy_snapshot(self):
        from api.snapshot_catalog import load_catalog
        ids = list(load_catalog(organization_id=None)["snapshots"])
        legacy = [i for i in ids if i.upper().endswith("_RPT_CURR")]
        self.assertEqual(legacy, [])
        self.assertTrue(all(i.startswith("rpt_") for i in ids), ids[:5])


class RoutingTests(unittest.TestCase):
    def test_an_oracle_org_runs_canvases_in_its_own_reporting_schema(self):
        """Exactly Ellensburg's path, now for every Oracle client."""
        from api.snapshot_catalog import get_snapshot, snapshot_backend
        snap = get_snapshot("rpt_bill", "dev")
        for org in _orgs():
            backend, dialect, schema = snapshot_backend(snap, org["id"])
            if org.get("engine") == "oracle":
                self.assertEqual((backend, dialect, schema),
                                 ("oracle", "oracle_dbt", "ORIGINBA_REPORTING"), org["id"])
            else:
                self.assertEqual((backend, dialect), ("postgres", "postgres"), org["id"])

    def test_the_legacy_dialect_no_longer_exists(self):
        """'oracle' meant the *_RPT_CURR world; only postgres and oracle_dbt remain."""
        from api.database_routes import _SCOPE_FENCES
        self.assertEqual(set(_SCOPE_FENCES), {"postgres", "oracle_dbt"})

    def test_the_legacy_fence_and_the_shape_shortcut_are_deleted(self):
        import api.snapshot_catalog as sc
        import api.sql_workspace_validator as v
        self.assertFalse(hasattr(v, "validate_oracle_cisadm_scope"))
        self.assertFalse(hasattr(sc, "is_warehouse"),
                         "is_warehouse meant 'is a dbt canvas'; everything is now")

    def test_build_query_refuses_the_retired_dialect(self):
        """'oracle' was the legacy path: unquoted UPPER_SNAKE identifiers against CISADM.
        A caller still passing it must fail loudly, not be routed there in silence."""
        from api.query_builder import QueryValidationError, build_query
        with self.assertRaises(QueryValidationError):
            build_query(table_name="rpt_bill", allowed_fields={"Bill Date"}, trusted_measures=set(),
                        dimensions=[], measures=[{"field": "*", "agg": "count"}], filters=[],
                        limit=10, dialect="oracle", schema="CISADM")

    def test_the_sql_workspace_still_reaches_cisadm_the_schema(self):
        """Retiring the snapshot catalog must not retire the schema analysts know."""
        from api.sql_workspace_validator import validate_oracle_reporting_scope
        validate_oracle_reporting_scope("SELECT USER_ID FROM CISADM.C1_CC_LOG")
        validate_oracle_reporting_scope(
            "SELECT b.\"Bill ID\" FROM ORIGINBA_REPORTING.RPT_BILL b")


class RequiredDateFieldIsGoneTests(unittest.TestCase):
    """A CISADM-era notion: a snapshot too large to read without a mandatory window.
    No dbt canvas ever set it, and the copies of its fallback caused a real bug."""

    def test_build_query_no_longer_takes_it(self):
        from api.query_builder import build_query
        self.assertNotIn("required_date_field", inspect.signature(build_query).parameters)

    def test_the_catalog_no_longer_carries_it(self):
        from api.snapshot_catalog import list_snapshots, load_catalog
        for snap in list_snapshots(organization_id=None):
            self.assertNotIn("required_date_field", snap, snap["id"])
        for sid, meta in load_catalog(organization_id=None)["snapshots"].items():
            self.assertNotIn("required_date_field", meta, sid)
            self.assertNotIn("required_date_label", meta, sid)

    def test_the_window_rule_reads_only_the_measured_default(self):
        from api.reporting_dates import window_date_field, window_date_label
        self.assertEqual(window_date_field({"default_date_field": "Bill Date"}), "Bill Date")
        self.assertIsNone(window_date_field({}))
        self.assertEqual(window_date_label({"date_fields": [{"id": "Bill Date",
                                                             "label": "Bill Date"}]},
                                           "Bill Date"), "Bill Date")


class NoMentionTests(unittest.TestCase):
    """The requirement is literal: the legacy shape is not MENTIONED in the app."""

    LEGACY = re.compile(r"_RPT_CURR|catalog_cisadm|cisadm[-_ ]catalog|required_date_field"
                        r"|required_date_label|is_warehouse|validate_oracle_cisadm_scope",
                        re.IGNORECASE)

    def _hits(self, root: Path, exts: tuple[str, ...]) -> list[str]:
        hits = []
        for p in sorted(root.rglob("*")):
            if p.suffix not in exts or "node_modules" in p.parts or p.name.endswith(".test.ts"):
                continue
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if self.LEGACY.search(line):
                    hits.append(f"{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}")
        return hits

    def test_the_api_does_not_mention_the_legacy_shape(self):
        hits = self._hits(ROOT / "api", (".py",))
        self.assertEqual(hits, [], "\n" + "\n".join(hits))

    def test_the_frontend_does_not_mention_the_legacy_shape(self):
        hits = self._hits(ROOT / "apps" / "analytics-portal" / "src", (".ts", ".tsx"))
        self.assertEqual(hits, [], "\n" + "\n".join(hits))

    def test_config_does_not_mention_the_legacy_shape(self):
        # CISADM the SCHEMA is legitimately named (it is where the extracts come from);
        # only the catalog SHAPE is retired.
        text = (ROOT / "config" / "portal_organizations.json").read_text()
        self.assertNotRegex(text, r'"catalog":\s*"cisadm"|catalog back to cisadm|cisadm[-_ ]catalog')


if __name__ == "__main__":
    unittest.main()
