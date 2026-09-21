"""The SQL report pack (scripts/jaspersoft/generate_sql_report_pack.py): the committed JRXML is
what the generator emits and is the JRXML 7 model, the SQL keeps the portable conventions, the
subreport wiring is complete, the REST deploy descriptor has the shape JRS 10 accepts, and --
when a JDK and the JasperReports 7.0.7 classpath are at hand -- every file compiles on the
engine JasperReports Server 10.0 runs."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import generate_sql_report_pack as g  # noqa: E402

FILES = [p for s in g.SPECS for p in (g.REPORTS / f"{s.name}.jrxml", g.SUBS / f"{s.sub.name}.jrxml")]


class Committed(unittest.TestCase):
    def test_the_committed_files_are_what_the_generator_emits(self):
        for s in g.SPECS:
            self.assertEqual((g.REPORTS / f"{s.name}.jrxml").read_text(), g.main_jrxml(s), s.name)
            self.assertEqual((g.SUBS / f"{s.sub.name}.jrxml").read_text(), g.sub_jrxml(s), s.sub.name)

    def test_every_file_is_jrxml_7(self):
        # the SmartCity server is JasperReports Server 10.0 (JasperReports 7); the 6.x model
        # does not load there. scripts/validate_jrxml_schema.py checks the 6.x element order
        # and does not apply to these files.
        for f in FILES:
            text = f.read_text()
            self.assertNotIn("xmlns=", text.split("\n")[1], f"{f.name}: a JRXML 7 root carries no namespace")
            self.assertIn('<element kind="textField"', text, f.name)
            self.assertNotIn("<queryString", text, f.name); self.assertIn('<query language="SQL">', text, f.name)
            self.assertNotIn("isBold", text, f.name); self.assertNotIn("<reportElement", text, f.name)

    def test_input_controls_exist_for_every_main_report(self):
        for s in g.SPECS:
            self.assertTrue((g.CONTROLS / f"{s.name}_input_controls.json").exists(), s.name)
            self.assertTrue((g.CONTROLS / f"{s.name}_input_controls_rest.json").exists(), s.name)


class Sql(unittest.TestCase):
    def test_portable_conventions_and_no_client_codes(self):
        for s in g.SPECS:
            for sql in (s.main_sql(), s.sub_sql()):
                up = sql.upper()
                for bad in ("NVL(", "SYSDATE", "DECODE(", "ROWNUM", "$P!{"):
                    self.assertNotIn(bad, up, f"{s.name}: {bad}")
                if re.search(r"\b\w+_L\b", up):
                    self.assertIn("LANGUAGE_CD = 'ENG'", up, f"{s.name}: label join without a language")
                self.assertIn("INTERVAL '1' DAY", sql, f"{s.name}: inclusive TO date")
                for flag in re.findall(r"\b\w+\.(bseg_stat_flg|bill_stat_flg|adj_status_flg|freeze_sw|est_sw|main_cust_sw|name_type_flg)\b", sql):
                    self.assertIn(f"TRIM(", sql, flag)
            # only lifecycle constants are literal: '50' frozen, 'C' completed, 'Y', 'ENG', 'PRIM'
            literals = set(re.findall(r"= '([^']+)'", s.main_sql() + s.sub_sql()))
            self.assertTrue(literals <= {"50", "C", "Y", "ENG", "PRIM"}, f"{s.name}: {literals}")

    def test_subreport_wiring(self):
        for s in g.SPECS:
            main = g.main_jrxml(s)
            self.assertIn(f'"repo:{s.sub.name}"', main, "the subreport is a local resource of the unit, named without a path")
            for p in ("FROM_DT", "TO_DT", *s.sub.keys(), *s.all_params()):
                self.assertIn(f'<parameter name="{p}"><expression>', main, f"{s.name}: {p}")
            self.assertIn("$P{REPORT_CONNECTION}", main)
            for k in s.sub.keys():
                self.assertIn(f"$P{{{k}}}", s.sub.sql, f"{s.sub.name}: key {k} unused in its SQL")
                self.assertIn(f'name="{k}"', g.sub_jrxml(s))

    def test_every_report_has_optional_filters_that_reach_both_queries(self):
        for s in g.SPECS:
            self.assertGreaterEqual(len(s.filters), 3, s.name)
            main, sub = s.main_sql(), s.sub_sql()
            for f in s.filters:
                # optional either way: a null single value, or a null/empty collection ($X{IN} is then true)
                opt = f"$X{{IN, " if f.multi else f"$P{{{f.param}}} IS NULL OR"
                self.assertIn(opt, main, f"{s.name}: {f.param} not optional in main")
                self.assertIn(opt, sub, f"{s.name}: {f.param} not optional in sub")
                if f.multi:
                    self.assertIn(f", {f.param}}}", main)
                    self.assertIn(f'<parameter name="{f.param}" class="java.util.Collection">', g.main_jrxml(s))
                self.assertIn(f'<parameter name="{f.param}"', g.sub_jrxml(s), f"{s.sub.name}: {f.param} undeclared")
            # the filters sit inside the WHERE, before any GROUP BY
            for sql in (main, sub):
                if "GROUP BY" in sql:
                    self.assertLess(max(sql.rfind("IS NULL OR"), sql.rfind("$X{IN")), sql.find("\nGROUP BY"), s.name)
            self.assertNotIn("/*FILTERS*/", main + sub)

    def test_columns_fill_the_page(self):
        for s in g.SPECS:
            self.assertEqual(sum(c.width for c in s.columns), g.COL_W, s.name)
            self.assertEqual(sum(c.width for c in s.sub.columns), g.COL_W - 24, s.sub.name)
            # a subreport shares the main grid: every numeric column sits at a main column's x
            edges = set(); x = 0
            for c in s.columns:
                x += c.width; edges.add(x)
            x = 24
            for c in s.sub.columns:
                x += c.width
                if c.name and c.align == "Right":
                    self.assertIn(x, edges, f"{s.sub.name}.{c.name} right edge {x} is off the main grid")


def _jr7_classpath() -> str | None:
    """The JasperReports 7.0.7 classpath from the letterprint service (the JRS 10 engine)."""
    pom = Path.home() / "originba-letterprint" / "service"
    if not (pom / "pom.xml").exists():
        return None
    out = Path(tempfile.gettempdir()) / "originba_jr7.cp"
    if not out.exists():
        r = subprocess.run([str(pom / "mvnw"), "-q", "dependency:build-classpath", f"-Dmdep.outputFile={out}"],
                           cwd=pom, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            return None
    return out.read_text().strip()


def _jdk() -> tuple[str, str] | None:
    for home in ("/opt/homebrew/opt/openjdk@21", "/opt/homebrew/opt/openjdk"):
        if Path(home, "bin", "javac").exists():
            return f"{home}/bin/javac", f"{home}/bin/java"
    if shutil.which("javac") and shutil.which("java"):
        return shutil.which("javac"), shutil.which("java")
    return None


class CompilesOnJasperReports7(unittest.TestCase):
    def test_every_file_compiles(self):
        cp, jdk = _jr7_classpath(), _jdk()
        if not cp or not jdk:
            self.skipTest("needs the letterprint service checkout and a JDK 11+")
        javac, java = jdk
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "CompileCheck.java"
            src.write_text("""import net.sf.jasperreports.engine.JasperCompileManager;
public class CompileCheck { public static void main(String[] a) throws Exception { int bad = 0;
  for (String f : a) { try { JasperCompileManager.compileReport(f); System.out.println("OK   " + f); }
    catch (Exception e) { bad++; System.out.println("FAIL " + f + " : " + e.getMessage().split("\\n")[0]); } }
  System.exit(bad == 0 ? 0 : 1); } }""")
            self.assertEqual(subprocess.run([javac, "--release", "11", "-cp", cp, str(src)], capture_output=True, text=True, cwd=d).returncode, 0)
            r = subprocess.run([java, "-cp", f"{cp}:{d}", "CompileCheck", *map(str, FILES)], capture_output=True, text=True, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__":
    unittest.main()


class RestDescriptor(unittest.TestCase):
    """What jrs_deploy_report_units.py PUTs: the shape JRS 10 accepted on 2026-09-17."""

    def test_descriptor_shape(self):
        import jrs_deploy_report_units as d
        for s in g.SPECS:
            desc = d.descriptor(s, "/organizations/organization_1/organizations/X/DataSource/X_DS")
            self.assertEqual(desc["dataSource"], {"dataSourceReference": {"uri": "/organizations/organization_1/organizations/X/DataSource/X_DS"}})
            self.assertEqual(desc["jrxml"]["jrxmlFile"]["type"], "jrxml")
            res = desc["resources"]["resource"]          # ClientReportUnitResourceListWrapper
            self.assertEqual([r["name"] for r in res], [s.sub.name])
            self.assertIn(f'"repo:{s.sub.name}"', g.main_jrxml(s))
            ids = [c["inputControl"]["uri"].rsplit("/", 1)[-1] for c in desc["inputControls"]]
            self.assertEqual(ids, [ic["id"] for ic in g.controls(s)[0]["inputControls"]])
            for c in desc["inputControls"]:
                ic = c["inputControl"]
                if ic["type"] in (d.SINGLE_SELECT_QUERY, d.MULTI_SELECT_QUERY):
                    q = ic["query"]["query"]
                    self.assertTrue(q["value"].upper().startswith("SELECT ") and " AS CODE" in q["value"] and " AS DESCR" in q["value"])
                    self.assertIn("LANGUAGE_CD = 'ENG'", q["value"].upper())
                    self.assertIn("EXISTS (SELECT 1 FROM CISADM.", q["value"], f"{s.name}.{ic['uri']}: a pick-list shows codes with activity")
                    self.assertIn("CURRENT_DATE - INTERVAL '3' YEAR", q["value"], f"{s.name}.{ic['uri']}: activity means the last 3 years")
                    self.assertEqual((ic["valueColumn"], ic["visibleColumns"]), ("CODE", ["DESCR"]))
                    self.assertEqual(q["dataSource"]["dataSourceReference"]["uri"], "/organizations/organization_1/organizations/X/DataSource/X_DS")
                else:
                    self.assertIn(ic["dataType"]["dataType"]["type"], ("text", "number", "date"))
            self.assertNotIn("CLIENT_NAME", ids)

    def test_pick_lists_where_the_client_configures_the_codes(self):
        for s in g.SPECS:
            lists = {f.param for f in s.filters if f.lov_sql}
            self.assertTrue(lists, s.name)
            self.assertTrue(all(f.lov_sql for f in s.filters if f.param.endswith(("_CD_F", "DIVISION_F", "DST_ID_F", "FLG_F"))), s.name)
            self.assertIn(s.window_label, g.main_jrxml(s))


class MultiSelect(unittest.TestCase):
    def test_bill_cycles_and_tender_types_take_several_values(self):
        import jrs_deploy_report_units as d
        multi = {(s.name, f.param) for s in g.SPECS for f in s.filters if f.multi}
        self.assertEqual(multi, {("billing_by_cycle_period", "BILL_CYC_CD_F"), ("payments_by_tender_type_period", "TENDER_TYPE_CD_F")})
        for s in g.SPECS:
            desc = d.descriptor(s, "/x/DataSource/X_DS")
            for c in desc["inputControls"]:
                ic = c["inputControl"]; name = ic["uri"].rsplit("/", 1)[-1]
                self.assertEqual(ic["type"] == d.MULTI_SELECT_QUERY, (s.name, name) in multi, f"{s.name}.{name}")
