"""Data quality for Oracle in-database organizations (Ellensburg first).

`/dq/findings` only knew the Postgres warehouse, so an organization whose canvases live
in its own C2M instance (engine oracle, ORIGINBA_REPORTING) was told "No reporting
warehouse is configured for this organization" while its warehouse was being rebuilt
every six hours. Such an organization runs the GENERATED Oracle rules
(originba_dbt dq_rules/rules.oracle.yml, bundled as config/dq_rules.oracle.yml) through
the portal's Oracle connection, with the same wrapper, cap, per-rule isolation and
response shape as Postgres, and its acknowledgements expire on the warehouse's build
stamp. Postgres organizations are unchanged.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import dq_routes  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

ORACLE_RULES = [
    {"id": "usage_after_vacancy", "key_column": "Service Point ID", "object": "Service Point",
     "severity": "action", "title": "Usage after vacancy", "action": "Reconcile.",
     "sql": 'SELECT "Service Point ID" FROM ORIGINBA_REPORTING.RPT_PREMISE_SP\n'
            'WHERE "Usage After Vacancy" = 1\n'},
    {"id": "sp_no_installed_device", "key_column": "Service Point ID", "object": "Service Point",
     "severity": "review", "title": "No installed device", "action": "Dispatch.",
     "sql": 'SELECT "Service Point ID" FROM ORIGINBA_REPORTING.RPT_PREMISE_SP\n'
            'WHERE NOT "Has Installed Device" = 1\n'},
]


def _ctx():
    return AuthContext(id="u1", email="u1@utility.gov", display_name="u1", role="editor",
                       client_id="ellensburg", organization_id="ellensburg",
                       organization_name="Ellensburg", permissions={"portal:read"},
                       workstreams=["*"], row_rules=())


class OracleOrgHarness(unittest.TestCase):
    """An Oracle organization with a stubbed Oracle executor and build stamp."""

    engine = "oracle"

    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        rules = tmp / "rules.oracle.yml"
        rules.write_text(yaml.safe_dump(ORACLE_RULES, sort_keys=False))
        self.executed: list[str] = []
        from api import summary_cache
        summary_cache.clear()
        self.addCleanup(summary_cache.clear)
        self.stamp = "20260929063012:20260929063015:38"
        self.failing: set[str] = set()
        patches = [
            mock.patch.object(dq_routes, "require_org_for_data", return_value="ellensburg"),
            mock.patch.object(dq_routes, "org_backend", return_value=(self.engine, "dbt")),
            mock.patch.object(dq_routes, "ACK_DIR", tmp / "acks"),
            mock.patch.object(dq_routes, "DEFAULT_ORACLE_RULES", tmp / "absent.yml"),
            mock.patch.object(dq_routes, "BUNDLED_ORACLE_RULES", rules),
            mock.patch.object(dq_routes, "oracle_query", side_effect=self._oracle),
            mock.patch.object(dq_routes, "data_version", side_effect=lambda org: self.stamp),
            mock.patch.object(dq_routes, "warehouse_connection",
                              side_effect=AssertionError("an Oracle org must not borrow the Postgres pool")),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _oracle(self, sql, binds=None, *, organization_id, max_rows):
        self.assertEqual(organization_id, "ellensburg")
        self.executed.append(sql)
        for rule_id in self.failing:
            if next(r["sql"] for r in ORACLE_RULES if r["id"] == rule_id).strip() in sql:
                raise RuntimeError("ORA-00942: table or view does not exist\nHelp: ...")
        total = 150
        rows = [[f"SP{i:03d}", total] for i in range(min(total, max_rows))]
        return ["Service Point ID", "_dq_total"], rows


class OracleOrgFindingsTests(OracleOrgHarness):
    def test_an_oracle_org_runs_the_oracle_rules_and_is_configured(self):
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertTrue(out["configured"])
        self.assertEqual([r["id"] for r in out["rules"]], ["usage_after_vacancy", "sp_no_installed_device"])
        self.assertEqual(len(self.executed), 2)
        self.assertTrue(any("ORIGINBA_REPORTING.RPT_PREMISE_SP" in s for s in self.executed))

    def test_the_response_has_the_postgres_shape(self):
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertLessEqual({"configured", "refresh_marker", "act_now", "review", "acknowledged", "rules"},
                             set(out))
        rule = out["rules"][0]
        for key in ("columns", "rows", "count", "total", "capped", "row_keys", "acked_rows"):
            self.assertIn(key, rule)
        self.assertEqual(rule["columns"], ["Service Point ID"])
        self.assertEqual(rule["total"], 150)
        self.assertEqual(rule["count"], dq_routes.ROW_CAP)
        self.assertTrue(rule["capped"])
        self.assertEqual(out["act_now"], 150)

    def test_the_wrapper_counts_everything_and_fetches_one_past_the_cap(self):
        dq_routes.dq_findings(ctx=_ctx())
        wrapped = self.executed[0]
        self.assertIn("count(*) over ()", wrapped)
        # Oracle refuses an unquoted identifier that starts with an underscore (ORA-00911)
        # and would upper-case one that did not, so the total column is quoted.
        self.assertIn(f'as "{dq_routes.TOTAL_COL}"', wrapped)

    def test_a_failing_rule_is_isolated(self):
        self.failing = {"usage_after_vacancy"}
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertTrue(out["configured"])
        by_id = {r["id"]: r for r in out["rules"]}
        failed, fine = by_id["usage_after_vacancy"], by_id["sp_no_installed_device"]
        self.assertTrue(failed["error"].startswith("ORA-00942"))
        self.assertEqual((failed["rows"], failed["count"], failed["total"]), ([], 0, 0))
        self.assertIsNone(fine.get("error"))
        self.assertEqual(fine["total"], 150)

    def test_an_error_with_no_message_is_still_isolated(self):
        # str(e).splitlines()[0] raised IndexError on an empty message and took the whole
        # page down; found by the concurrency test below via a broken barrier.
        fetch = self._oracle

        def silent_failure(sql, binds=None, *, organization_id, max_rows):
            if "Usage After Vacancy" in sql:
                raise RuntimeError()
            return fetch(sql, binds, organization_id=organization_id, max_rows=max_rows)

        with mock.patch.object(dq_routes, "oracle_query", side_effect=silent_failure):
            out = dq_routes.dq_findings(ctx=_ctx())
        by_id = {r["id"]: r for r in out["rules"]}
        self.assertEqual(by_id["usage_after_vacancy"]["error"], "RuntimeError")
        self.assertEqual(by_id["sp_no_installed_device"]["total"], 150)

    def test_the_rules_run_side_by_side_within_a_bound(self):
        # Serially the 22 rules took 101 s on Ellensburg over the VPN (2026-09-29), the
        # CISADM scans and the calc-line regex being most of it. They run side by side,
        # but never on more sessions than ORACLE_RULE_WORKERS: the org's pool also serves
        # every other page.
        import threading
        import time
        both_in_flight = threading.Barrier(2, timeout=5)
        lock, in_flight, peak = threading.Lock(), [0], [0]
        fetch = self._oracle

        def concurrent(sql, binds=None, *, organization_id, max_rows):
            with lock:
                in_flight[0] += 1
                peak[0] = max(peak[0], in_flight[0])
            try:
                both_in_flight.wait()   # breaks (and the rule errors) if rules run one at a time
                time.sleep(0.05)
                return fetch(sql, binds, organization_id=organization_id, max_rows=max_rows)
            finally:
                with lock:
                    in_flight[0] -= 1

        with mock.patch.object(dq_routes, "oracle_query", side_effect=concurrent):
            out = dq_routes.dq_findings(ctx=_ctx())
        self.assertEqual([r.get("error") for r in out["rules"]], [None, None])
        self.assertLessEqual(peak[0], dq_routes.ORACLE_RULE_WORKERS)

    def test_an_unbuilt_warehouse_is_not_configured_rather_than_a_page_of_errors(self):
        # citycorp, newark and the others have Oracle credentials but no ORIGINBA_REPORTING
        self.failing = {r["id"] for r in ORACLE_RULES}
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertFalse(out["configured"])
        self.assertEqual(out["rules"], [])


class OracleOrgAcknowledgementTests(OracleOrgHarness):
    def test_the_refresh_marker_is_the_build_stamp(self):
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertEqual(out["refresh_marker"], self.stamp)

    def test_the_page_is_told_when_the_tables_were_built_not_the_raw_stamp(self):
        # Ellensburg 2026-09-29 printed "data as of 20260928180601:20260910084138:39". The build
        # is the LAST_DDL half: statistics can be regathered (09-28) without a rebuild (09-10).
        self.stamp = "20260928180601:20260910084138:39"
        self.assertEqual(dq_routes.dq_findings(ctx=_ctx())["built_at"], "2026-09-10T08:41:38")
        self.stamp = None
        self.assertIsNone(dq_routes.dq_findings(ctx=_ctx())["built_at"])

    def test_an_ack_lasts_until_the_warehouse_is_rebuilt(self):
        first = dq_routes.dq_findings(ctx=_ctx())
        key = first["rules"][0]["row_keys"][0]
        self.assertTrue(dq_routes.dq_ack(payload={"key": key}, ctx=_ctx())["ok"])

        again = dq_routes.dq_findings(ctx=_ctx())
        self.assertIn(key, again["rules"][0]["acked_row_keys"])

        self.stamp = "20260929123000:20260929123004:38"   # the next six-hourly build
        rebuilt = dq_routes.dq_findings(ctx=_ctx())
        self.assertNotIn(key, rebuilt["rules"][0]["acked_row_keys"])
        self.assertIn(key, rebuilt["rules"][0]["row_keys"])


class RuleFileTests(unittest.TestCase):
    def test_oracle_prefers_the_sibling_generated_file_then_the_bundled_copy(self):
        tmp = Path(tempfile.mkdtemp())
        sibling, bundled = tmp / "rules.oracle.yml", tmp / "dq_rules.oracle.yml"
        with mock.patch.object(dq_routes, "DEFAULT_ORACLE_RULES", sibling), \
             mock.patch.object(dq_routes, "BUNDLED_ORACLE_RULES", bundled):
            self.assertEqual(dq_routes._rules_path("oracle"), bundled)
            sibling.write_text("[]")
            self.assertEqual(dq_routes._rules_path("oracle"), sibling)

    def test_the_bundled_oracle_copy_is_the_generated_oracle_rules(self):
        text = dq_routes.BUNDLED_ORACLE_RULES.read_text()
        self.assertTrue(text.startswith("# GENERATED"))
        rules = yaml.safe_load(text)
        postgres = yaml.safe_load(dq_routes.BUNDLED_RULES.read_text())
        self.assertEqual([r["id"] for r in rules], [r["id"] for r in postgres])
        for r in rules:
            self.assertNotIn("reporting.", r["sql"])
            self.assertNotIn("::", r["sql"])

    def test_the_bundled_oracle_copy_matches_the_sibling_when_there_is_one(self):
        if not dq_routes.DEFAULT_ORACLE_RULES.exists():
            self.skipTest("no sibling originba_dbt checkout with rules.oracle.yml")
        self.assertEqual(dq_routes.BUNDLED_ORACLE_RULES.read_text(),
                         dq_routes.DEFAULT_ORACLE_RULES.read_text(),
                         "refresh: cp ../originba_dbt/dq_rules/rules.oracle.yml config/dq_rules.oracle.yml")


class PostgresOrgUnchangedTests(unittest.TestCase):
    def test_a_postgres_org_runs_the_postgres_rules_on_the_warehouse_pool(self):
        tmp = Path(tempfile.mkdtemp())
        rules = tmp / "rules.yml"
        rules.write_text(yaml.safe_dump([{**ORACLE_RULES[0],
                                          "sql": 'select "Service Point ID" from reporting.rpt_premise_sp'}]))
        cur = mock.MagicMock()
        cur.description = [("Service Point ID",), ("_dq_total",)]
        cur.fetchmany.return_value = [["SP1", 1]]
        cur.fetchone.return_value = ["2026-09-28 06:31:02"]
        conn = mock.MagicMock()
        conn.cursor.return_value = cur
        pool = mock.MagicMock()
        pool.__enter__.return_value = conn
        with mock.patch.object(dq_routes, "require_org_for_data", return_value="demo25"), \
             mock.patch.object(dq_routes, "org_backend", return_value=("postgres", "dbt")), \
             mock.patch.object(dq_routes, "warehouse_configured", return_value=True), \
             mock.patch.object(dq_routes, "warehouse_connection", return_value=pool), \
             mock.patch.object(dq_routes, "ACK_DIR", tmp / "acks"), \
             mock.patch.dict("os.environ", {"DQ_RULES_PATH": str(rules)}), \
             mock.patch.object(dq_routes, "oracle_query",
                               side_effect=AssertionError("a Postgres org must not reach Oracle")), \
             mock.patch.object(dq_routes, "data_version", return_value="pg-build-1"):   # the cache key only
            out = dq_routes.dq_findings(ctx=_ctx())
        self.assertTrue(out["configured"])
        self.assertEqual(out["rules"][0]["rows"], [["SP1"]])
        self.assertEqual(out["refresh_marker"], "2026-09-28 06:31:02")   # acks keep the load watermark
        self.assertEqual(out["built_at"], "2026-09-28T06:31:02")
        executed = [c.args[0] for c in cur.execute.call_args_list]
        self.assertIn("from reporting.rpt_premise_sp", executed[0])
        self.assertIn("max(load_dttm)::text from staging.stg_financial_txn", executed[-1])


class OracleOrgCachingTests(OracleOrgHarness):
    """The rules take ~40 s on Ellensburg; their results change only when the warehouse is
    rebuilt, so they are kept until the build stamp moves (the home page's cache, 12 h cap).
    Acknowledgements are applied on every request, never baked into what is kept."""

    def test_a_second_visit_is_served_without_running_the_rules(self):
        dq_routes.dq_findings(ctx=_ctx())
        ran = len(self.executed)
        dq_routes.dq_findings(ctx=_ctx())
        self.assertEqual(len(self.executed), ran)
        self.stamp = "20260929123000:20260929123004:38"
        dq_routes.dq_findings(ctx=_ctx())
        self.assertEqual(len(self.executed), 2 * ran)

    def test_acknowledgements_apply_to_kept_results_without_changing_them(self):
        key = dq_routes.dq_findings(ctx=_ctx())["rules"][0]["row_keys"][0]
        dq_routes.dq_ack(payload={"key": key}, ctx=_ctx())
        self.assertIn(key, dq_routes.dq_findings(ctx=_ctx())["rules"][0]["acked_row_keys"])
        dq_routes.dq_unack(payload={"key": key}, ctx=_ctx())
        self.assertIn(key, dq_routes.dq_findings(ctx=_ctx())["rules"][0]["row_keys"])

    def test_the_warmer_builds_the_rules_after_a_rebuild(self):
        from api import cache_warmer as cw
        cw.reset()
        with mock.patch.object(cw, "data_version", return_value="V1"), \
             mock.patch.object(cw, "_workstreams", return_value=[]), \
             mock.patch.object(cw, "_opening_reports", return_value=[]), \
             mock.patch("api.snapshot_explorer.cached_home_summary", return_value={"kpis": []}), \
             mock.patch("api.ori_series.cached_history", return_value=({}, {})):
            self.assertIn("data quality", cw.warm_once("ellensburg"))
        ran = len(self.executed)
        self.assertGreater(ran, 0)
        dq_routes.dq_findings(ctx=_ctx())
        self.assertEqual(len(self.executed), ran)   # the page is served what the warmer built

    def test_a_run_cut_off_by_a_dropped_connection_is_not_kept(self):
        # Ellensburg 2026-09-29: the laptop slept mid-warm; four rules failed DPY-4011 / ORA-12262
        # and that half result was kept until the next rebuild
        first = ORACLE_RULES[0]["id"]
        original = self._oracle

        def flaky(sql, binds=None, *, organization_id, max_rows):
            if first in self.cut and ORACLE_RULES[0]["sql"].strip() in sql:
                raise RuntimeError("DPY-4011: the database or network closed the connection")
            return original(sql, binds, organization_id=organization_id, max_rows=max_rows)
        self.cut = {first}
        with mock.patch.object(dq_routes, "oracle_query", side_effect=flaky):
            dq_routes.dq_findings(ctx=_ctx())
            self.cut = set()
            again = dq_routes.dq_findings(ctx=_ctx())
        self.assertFalse(any(r.get("error") for r in again["rules"]))
        from api.executive_dashboard import is_not_connected_error
        self.assertTrue(is_not_connected_error("ORA-12262: Cannot connect to database. Could not resolve hostname"))

    def test_an_outage_is_not_kept(self):
        self.failing = {r["id"] for r in ORACLE_RULES}
        dq_routes.dq_findings(ctx=_ctx())
        ran = len(self.executed)
        self.failing = set()
        out = dq_routes.dq_findings(ctx=_ctx())
        self.assertGreater(len(self.executed), ran)
        self.assertTrue(out["configured"])


if __name__ == "__main__":
    unittest.main()
