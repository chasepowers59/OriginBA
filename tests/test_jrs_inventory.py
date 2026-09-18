"""The inventory tool's offline half: unpacking a real server export into the committed shape
(passwords redacted, everything else verbatim), summarizing it, and diffing two trees while
ignoring what the server changes on every export (dates, versions, the organization path)."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import jrs_inventory as inv  # noqa: E402

REP8 = ROOT / "domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_client_import.zip"


class Unpack(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_a_real_export_unpacks_with_the_password_redacted_and_content_verbatim(self):
        n = inv.unpack(REP8.read_bytes(), self.dir / "Newark1")
        self.assertGreater(n, 5)
        ds = (self.dir / "Newark1/resources/DataSource/Newark1_DS.xml").read_text()
        self.assertIn("<connectionPassword>REDACTED</connectionPassword>", ds)
        self.assertNotIn("4A5253", ds.split("<connectionPassword>")[1][:20])
        jrxml = (self.dir / "Newark1/resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance_files/main_jrxml.data").read_bytes()
        self.assertIn(b"<jasperReport", jrxml)

    def test_generated_topic_jrxml_and_rendered_outputs_stay_in_the_backup_only(self):
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("resources/X/v.xml", "<adhocDataView/>"); z.writestr("resources/X/v_files/stateXML.data", "<state/>")
            z.writestr("resources/X/v_files/topicJRXML.data", "<jasperReport/>"); z.writestr("resources/X/out.pdf", "%PDF")
        n = inv.unpack(buf.getvalue(), self.dir / "T")
        got = sorted(p.name for p in (self.dir / "T").rglob("*") if p.is_file())
        self.assertEqual(got, ["stateXML.data", "v.xml"]); self.assertEqual(n, 2)

    def test_summary_counts_types_and_names_datasources(self):
        inv.unpack(REP8.read_bytes(), self.dir / "Newark1")
        s = inv.summarize(self.dir / "Newark1")
        self.assertEqual(s["resources_by_type"].get("reportUnit"), 1)
        self.assertEqual(s["resources_by_type"].get("jdbcDataSource"), 1)
        self.assertEqual(s["datasources"][0]["user"], "JRS2C2M")
        self.assertTrue(any("Debt_Management" in f for f in s["folders"]))
        self.assertEqual(s["report_units"], ["/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance"])

    def test_diff_ignores_dates_versions_and_the_org_path(self):
        a, b = self.dir / "test/OrgA", self.dir / "prod/OrgB"
        inv.unpack(REP8.read_bytes(), a); inv.unpack(REP8.read_bytes(), b)
        unit = b / "resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance.xml"
        unit.write_text(unit.read_text().replace("<version>13</version>", "<version>14</version>")
                        .replace("2024-10-30T13:45:17.000Z", "2026-01-01T00:00:00.000Z"))
        with unittest.mock.patch.object(inv, "INVENTORY", self.dir):
            self.assertEqual(inv.diff("test:OrgA", "prod:OrgB", None), 0, "version and date churn is not a difference")
            (b / "resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance_files/main_jrxml.data").write_bytes(b"<jasperReport/>")
            self.assertEqual(inv.diff("test:OrgA", "prod:OrgB", "/SmartCity/Report"), 1, "content is")


import unittest.mock  # noqa: E402

if __name__ == "__main__":
    unittest.main()


def test_split_export_walks_only_the_named_folders(monkeypatch):
    """--split names the folders exported child by child; everything else stays one part."""
    tree = {
        "/": [("f", "/SmartCity"), ("f", "/DataSource")],
        "/SmartCity": [("f", "/SmartCity/Report"), ("f", "/SmartCity/Domain")],
        "/SmartCity/Report": [("f", "/SmartCity/Report/FDL_Trial_Balance"), ("r", "/SmartCity/Report/Loose")],
    }

    def fake_call(path, **_):
        folder = path.split("folderUri=")[1].split("&")[0]
        import urllib.parse as up
        kids = tree.get(up.unquote(folder), [])
        return 200, json.dumps({"resourceLookup": [
            {"uri": u, "resourceType": "folder" if k == "f" else "reportUnit"} for k, u in kids]})

    monkeypatch.setattr(inv, "_call", fake_call)
    assert inv._part_uris(["/SmartCity", "/SmartCity/Report"]) == [
        "/SmartCity/Report/Loose", "/SmartCity/Report/FDL_Trial_Balance", "/SmartCity/Domain", "/DataSource"]
    assert inv._part_uris([]) == ["/SmartCity", "/DataSource"]


def test_export_stuck_is_raised_not_exited(monkeypatch):
    calls = {"n": 0}

    def fake_call(path, **kw):
        if path.endswith("/export"):
            return 200, json.dumps({"id": "t1"})
        calls["n"] += 1
        return 200, json.dumps({"phase": "inprogress"})

    monkeypatch.setattr(inv, "_call", fake_call)
    monkeypatch.setattr(inv.time, "sleep", lambda s: None)
    monkeypatch.setattr(inv.time, "time", iter(range(0, 10_000)).__next__)
    with pytest.raises(inv.ExportStuck):
        inv.export_zip(["/x"], cap_seconds=5)


def test_cut_download_reexports_then_gives_up(monkeypatch):
    """A download cut mid-stream starts a NEW export (the server drops the old one), bounded."""
    exports = {"n": 0}

    def fake_call(path, **kw):
        if path.endswith("/export"):
            exports["n"] += 1
            return 200, json.dumps({"id": f"t{exports['n']}"})
        return 200, json.dumps({"phase": "finished"})

    def cut(path):
        raise inv.DownloadCut("download cut after 12024 KB (IncompleteRead)")

    monkeypatch.setattr(inv, "_call", fake_call)
    monkeypatch.setattr(inv, "_download", cut)
    with pytest.raises(inv.ExportStuck):
        inv.export_zip(["/x"], attempts=3)
    assert exports["n"] == 3
