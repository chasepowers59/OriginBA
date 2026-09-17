"""The SQL report pack (scripts/jaspersoft/generate_sql_report_pack.py): the committed JRXML is
what the generator emits, every file passes the schema validator, the SQL keeps the portable
conventions, the subreport wiring is complete, and -- when a JDK and the JasperReports 6.20
classpath are at hand -- every file compiles on the engine JRS 8.1 / 9.0 run."""
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

    def test_every_file_passes_the_schema_validator(self):
        for f in FILES:
            r = subprocess.run([sys.executable, str(ROOT / "scripts/validate_jrxml_schema.py"), str(f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{f.name}: {r.stdout} {r.stderr}")

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
            for p in ("FROM_DT", "TO_DT", s.sub.key_param, *s.all_params()):
                self.assertIn(f'<subreportParameter name="{p}">', main, f"{s.name}: {p}")
            self.assertIn("$P{REPORT_CONNECTION}", main)
            self.assertIn(f"$P{{{s.sub.key_param}}}", s.sub.sql)
            self.assertIn(f'name="{s.sub.key_param}"', g.sub_jrxml(s))

    def test_every_report_has_optional_filters_that_reach_both_queries(self):
        for s in g.SPECS:
            self.assertGreaterEqual(len(s.filters), 3, s.name)
            main, sub = s.main_sql(), s.sub_sql()
            for f in s.filters:
                self.assertIn(f"$P{{{f.param}}} IS NULL OR", main, f"{s.name}: {f.param} not optional in main")
                self.assertIn(f"$P{{{f.param}}} IS NULL OR", sub, f"{s.name}: {f.param} not optional in sub")
                self.assertIn(f'<parameter name="{f.param}"', g.sub_jrxml(s), f"{s.sub.name}: {f.param} undeclared")
            # the filters sit inside the WHERE, before any GROUP BY
            for sql in (main, sub):
                if "GROUP BY" in sql:
                    self.assertLess(sql.rfind("IS NULL OR"), sql.find("\nGROUP BY"), s.name)
            self.assertNotIn("/*FILTERS*/", main + sub)

    def test_columns_fill_the_page(self):
        for s in g.SPECS:
            self.assertEqual(sum(c.width for c in s.columns), g.COL_W, s.name)
            self.assertEqual(sum(c.width for c in s.sub.columns), g.COL_W - 24, s.sub.name)


def _jr_classpath() -> str | None:
    """The JasperReports 6.20.6 classpath from the letterprint verifier, if that checkout exists."""
    pom = Path.home() / "originba-letterprint" / "jrsverify"
    if not (pom / "pom.xml").exists():
        return None
    out = Path(tempfile.gettempdir()) / "originba_jr620.cp"
    if not out.exists():
        r = subprocess.run([str(pom / "mvnw"), "-q", "dependency:build-classpath", f"-Dmdep.outputFile={out}"],
                           cwd=pom, capture_output=True, text=True)
        if r.returncode != 0 or not out.exists():
            return None
    return out.read_text().strip()


def _javac() -> str | None:
    for c in ("/opt/homebrew/opt/openjdk@21/bin/javac", "/opt/homebrew/opt/openjdk/bin/javac", shutil.which("javac") or ""):
        if c and Path(c).exists():
            return c
    return None


class CompilesOnJasperReports620(unittest.TestCase):
    def test_every_file_compiles(self):
        cp, javac = _jr_classpath(), _javac()
        if not cp or not javac or not shutil.which("java"):
            self.skipTest("needs the letterprint jrsverify checkout, a JDK and java on PATH")
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "CompileCheck.java"
            src.write_text("""import net.sf.jasperreports.engine.JasperCompileManager;
public class CompileCheck { public static void main(String[] a) throws Exception { int bad = 0;
  for (String f : a) { try { JasperCompileManager.compileReport(f); System.out.println("OK   " + f); }
    catch (Exception e) { bad++; System.out.println("FAIL " + f + " : " + e.getMessage().split("\\n")[0]); } }
  System.exit(bad == 0 ? 0 : 1); } }""")
            self.assertEqual(subprocess.run([javac, "--release", "8", "-cp", cp, str(src)], capture_output=True, text=True, cwd=d).returncode, 0)
            r = subprocess.run(["java", "-cp", f"{cp}:{d}", "CompileCheck", *map(str, FILES)], capture_output=True, text=True, cwd=d)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__":
    unittest.main()


class JrsImportZip(unittest.TestCase):
    """The import zip is the server's own export shape (the manifest bundle was refused on DEV)."""

    @classmethod
    def setUpClass(cls):
        import zipfile
        import build_finance_pack_jrs_import as b
        cls.b = b
        cls.zip_path = Path(tempfile.mkdtemp()) / "pack.zip"
        b.build(cls.zip_path, "/DataSource/Origin_DEV_DS")
        cls.zf = zipfile.ZipFile(cls.zip_path)
        cls.names = cls.zf.namelist()

    def test_index_is_last_keyalias_first_and_names_the_datasource_and_roots(self):
        import xml.etree.ElementTree as ET
        import zipfile
        self.assertEqual(self.names[-1], "index.xml")
        self.assertEqual(self.names[0], "favorites/")
        self.assertEqual(self.zf.getinfo("favorites/").compress_type, zipfile.ZIP_DEFLATED)
        idx = self.zf.read("index.xml").decode()
        root = ET.fromstring(idx)
        first = list(root)[0]
        self.assertEqual((first.tag, first.get("name")), ("property", "keyalias"), "a server export starts with keyalias")
        self.assertTrue(first.get("value"))
        props = {p.get("name"): p.get("value") for p in root.findall("property")}
        self.assertTrue(props.get("encrypted"), "encrypted travels with keyalias, copied from a real export")
        self.assertEqual(props.get("jsVersion"), "8.1.0 PRO")
        self.assertNotIn("rootTenantId", props, "tenant-relative")
        self.assertIn("<resource>/DataSource/Origin_DEV_DS</resource>", idx, "the datasource must be in the batch")
        for r in sorted({g.FOLDERS[s.name] for s in g.SPECS}):
            self.assertIn(f"<folder>{r}</folder>", idx)
        self.assertIn("resources/DataSource/Origin_DEV_DS.xml", self.names)
        self.assertIn("resources/DataSource/.folder.xml", self.names)
        self.assertNotIn(" />", idx, "compact export formatting")

    def test_every_folder_on_the_path_has_a_folder_xml(self):
        import xml.etree.ElementTree as ET
        for n in self.names:
            if n.startswith("resources/") and n.count("/") > 1 and not n.endswith("/"):
                parts = n.split("/")[1:-1]
                for i in range(len(parts)):
                    if parts[i].endswith("_files"):
                        break
                    self.assertIn("resources/" + "/".join(parts[: i + 1]) + "/.folder.xml", self.names, n)
        for n in self.names:
            if n.endswith(".xml") and n != "index.xml":
                ET.fromstring(self.zf.read(n))

    def test_each_unit_references_files_that_exist_and_its_subreport_by_name(self):
        import re as _re
        for s in g.SPECS:
            rel = g.FOLDERS[s.name].strip("/")
            unit = self.zf.read(f"resources/{rel}/{s.name}.xml").decode()
            self.assertIn("<uri>/DataSource/Origin_DEV_DS</uri>", unit)
            for df in _re.findall(r'dataFile="([^"]+)"', unit):
                self.assertIn(f"resources/{rel}/{s.name}_files/{df}", self.names, df)
            main = self.zf.read(f"resources/{rel}/{s.name}_files/main_jrxml.data").decode()
            for ref in _re.findall(r'"repo:([^"]+)"', main):
                self.assertIn(f"<name>{ref}</name>", unit, f"{s.name}: repo:{ref} is not a resource of the unit")
            doc, _ = g.controls(s)
            self.assertEqual(unit.count('xsi:type="inputControl"'), len(doc["inputControls"]))
            for ic in doc["inputControls"]:
                self.assertIn(f"<name>{ic['id']}</name>", unit)
                self.assertIn(f'<parameter name="{ic["id"]}"', main, f"{s.name}: control {ic['id']} has no parameter")
