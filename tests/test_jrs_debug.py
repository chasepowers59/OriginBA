"""The debugger's pure parts, offline: reading a saved view's filters back as a person would,
patching a domain schema (a derived query, a join) without touching any id, pruning filters from
a view query, and the exact PUT/import calls a fix makes (dry run). Real inputs: the Fond du Lac
asset domain schema and the saved-filter shape the server returned on 2026-09-18."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/jaspersoft"))
import jrs_debug as dbg  # noqa: E402

SCHEMA = ROOT / "domains/manual_imports/fonddulac_asset_domain/schema.original.xml"

def filt(fid, inner):
    return {"function": {"operands": [{"string": {"value": fid}}, {"string": {"value": "DYNAMIC"}}, inner], "functionName": "filter"}}

QUERY = {"select": {"distinctFields": [{"field": "W1_ASSET_IDENTIFIER.W1_ID_VALUE"}, {"field": "W1_ASSET_NODE.CURR_NODE_ID"}]},
         "where": {"filterExpression": {"object": {"and": {"operands": [
             filt("filter_1", {"in": {"operands": [{"variable": {"name": "W1_ASSET.ASSET_TYPE_CD"}}, {"variable": {"name": "ASSET_TYPE_CD_1"}}]}}),
             filt("filter_2", {"in": {"operands": [{"variable": {"name": "DESCRIPTIONS.SA_TYPE_DESC"}}, {"list": {"items": []}}]}}),
             filt("filter_3", {"notEqual": {"operands": [{"variable": {"name": "W1_ASSET_NODE.CURR_NODE_ID"}}, {"variable": {"name": "CURR_NODE_ID_1"}}]}})]}}},
                   "parameters": [{"name": "ASSET_TYPE_CD_1", "expression": {"object": {"list": {"items": [{"string": {"value": "W-SMART-MTR"}}]}}}},
                                  {"name": "CURR_NODE_ID_1", "expression": {"object": {"NULL": {}}}}]}}


def test_filters_read_back_with_their_values_and_any_value_flag():
    fl = dbg.filters_of(QUERY)
    assert [f["field"] for f in fl] == ["W1_ASSET.ASSET_TYPE_CD", "DESCRIPTIONS.SA_TYPE_DESC", "W1_ASSET_NODE.CURR_NODE_ID"]
    assert fl[0]["values"] == [["W-SMART-MTR"]] and not fl[0]["any_value"]
    assert fl[1]["any_value"]
    assert fl[2]["op"] == "notEqual" and fl[2]["values"] == [None]


def test_patch_schema_changes_only_the_named_query_and_join(tmp_path):
    xml = SCHEMA.read_text()
    sql = tmp_path / "q.sql"; sql.write_text("SELECT AN.* FROM CISADM.W1_ASSET_NODE AN WHERE 1 < 2")
    out = dbg.patch_schema(xml, [f"SC_CURRENT_DISPOSITION={sql}"], ["W1_ASSET_NODE.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE=>SC_CURRENT_DISPOSITION.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE"])
    assert "WHERE 1 &lt; 2" in out
    assert '<join expr="SC_CURRENT_DISPOSITION.NODE_ID == SC_SP_EQUIPMENT.ID_VALUE" left="SC_CURRENT_DISPOSITION" right="SC_SP_EQUIPMENT"' in out
    import re
    ids = lambda s: re.findall(r'<item id="([^"]+)"', s)
    assert ids(out) == ids(xml) and out.count("<jdbcQuery") == xml.count("<jdbcQuery") and out.count("<join ") == xml.count("<join ")


def test_patch_schema_refuses_an_unknown_query_or_join(tmp_path):
    sql = tmp_path / "q.sql"; sql.write_text("select 1")
    with pytest.raises(SystemExit): dbg.patch_schema(SCHEMA.read_text(), [f"NOPE={sql}"], [])
    with pytest.raises(SystemExit): dbg.patch_schema(SCHEMA.read_text(), [], ["A.X == B.Y=>A.X == C.Y"])


def test_view_update_drops_a_filter_sets_a_value_and_puts_the_descriptor(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(dbg, "get", lambda uri, expanded=True: {"uri": uri, "query": {"multiLevel": json.loads(json.dumps(QUERY))}})
    monkeypatch.setattr(dbg, "put", lambda path, body, ctype, what: calls.append((path, json.loads(body), ctype)) or 0)
    dbg.view_update("/SmartCity/Report/X/v", ["W1_ASSET_NODE.CURR_NODE_ID"], ["ASSET_TYPE_CD=W-SMART-MTR,W-MTR"], ["W1_ASSET_NODE.CURR_NODE_ID=SC_CURRENT_DISPOSITION.CURR_NODE_ID_1"])
    path, body, ctype = calls[0]
    assert path == "/rest_v2/resources/SmartCity/Report/X/v" and ctype == "application/repository.adhocDataView+json"
    q = body["query"]["multiLevel"]
    assert "filter_3" not in json.dumps(q["where"]["filterExpression"]) and "filter_1" in json.dumps(q["where"]["filterExpression"])
    assert [i["string"]["value"] for i in q["where"]["parameters"][0]["expression"]["object"]["list"]["items"]] == ["W-SMART-MTR", "W-MTR"]
    assert q["select"]["distinctFields"][1]["field"] == "SC_CURRENT_DISPOSITION.CURR_NODE_ID_1"


def test_domain_apply_and_report_update_put_file_resources(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(dbg, "put", lambda path, body, ctype, what: calls.append((path, ctype)) or 0)
    f = tmp_path / "s.xml"; f.write_text("<schema/>"); j = tmp_path / "r.jrxml"; j.write_text("<jasperReport/>")
    dbg.domain_apply("/SmartCity/Report/FDL_Asset/SC_Asset_Domain", str(f)); dbg.report_update("/SmartCity/Report/X/r", str(j))
    assert calls == [("/rest_v2/resources/SmartCity/Report/FDL_Asset/SC_Asset_Domain_files/schema", "application/repository.file+json"),
                     ("/rest_v2/resources/SmartCity/Report/X/r_files/main_jrxml", "application/repository.file+json")]


def test_domain_copy_package_has_the_proven_shape():
    ds_zip = ROOT / "backups/jaspersoft/prod/20260918-071832/Fond_Du_Lac__DataSource.zip"
    if not ds_zip.exists():
        pytest.skip("needs the prod datasource export (gitignored backup)")
    import zipfile, io
    pkg = dbg._org_export_package("Fond_Du_Lac", "/SmartCity/Report/FDL_Asset", "SC_Asset_Domain_Fixed", "FDL Asset Domain (Fixed)", "x" * 300, SCHEMA.read_text(), ds_zip.read_bytes(), "FondDuLac_DS")
    z = zipfile.ZipFile(io.BytesIO(pkg)); names = z.namelist()
    assert names[-1] == "index.xml" and "resources/DataSource/FondDuLac_DS.xml" in names
    assert "resources/SmartCity/.folder.xml" in names and "resources/SmartCity/Report/FDL_Asset/SC_Asset_Domain_Fixed_files/schema.data" in names
    dom = z.read("resources/SmartCity/Report/FDL_Asset/SC_Asset_Domain_Fixed.xml").decode()
    assert len(dom.split("<description>")[1].split("</description>")[0]) <= 240      # ORA-12899 at 250
    idx = z.read("index.xml").decode(); assert 'rootTenantId" value="Fond_Du_Lac"' in idx and idx.index("/DataSource/FondDuLac_DS") < idx.index("SC_Asset_Domain_Fixed")
