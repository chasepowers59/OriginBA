"""The domain-set importer packages a generated set (originba_dbt jaspersoft/domains/<target>/) for one org:
the org's own datasource, the offering root, the Standard Offering workstream folders, one domain per data set."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import jrs_import_domain_set as ds  # noqa: E402

MANIFEST = """# Origin BA domains for Origin_DEV_DS

| Domain | File | Repository folder | One row per | Fields | Measures | What it is for |
| --- | --- | --- | --- | ---: | ---: | --- |
| Bill | `originba_bill_domain.xml` | `Domains/Billing_and_Rates` | bill | 28 | 6 | Bill-level questions: how many bills went out. |
| On/Off History | `originba_on_off_history_domain.xml` | `Domains/Meter_Operations` | on/off event | 19 | 1 | Every connect and disconnect. |
"""
SCHEMA = '<schema><resources><jdbcTable id="T" datasourceId="Origin_DEV_DS" datasourceTableName="T"/></resources></schema>'


def _ds_zip() -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("index.xml", '<export><property name="keyalias" value="k"/><property name="encrypted" value="true"/>'
                                '<property name="jsVersion" value="10.0.0 PRO"/></export>')
        z.writestr("resources/DataSource/Origin_DEV_DS.xml", "<jdbcDataSource/>")
    return out.getvalue()


def test_manifest_rows():
    rows = ds.parse_manifest(MANIFEST)
    assert [r["label"] for r in rows] == ["Bill", "On/Off History"]
    assert rows[1] == {"label": "On/Off History", "file": "originba_on_off_history_domain.xml", "folder": "Meter_Operations",
                       "grain": "on/off event", "purpose": "Every connect and disconnect."}


def test_names_follow_the_standard_offering():
    assert ds.resource_name("On/Off History") == "On_Off_History___Domain"
    assert ds.resource_label("On/Off History") == "On/Off History - Domain"
    assert ds.folder_label("Billing_and_Rates") == "Billing and Rates"
    assert ds.folder_label("Customer_Operations") == "Customer Operations"


def test_description_fits_the_server_limit():
    row = {"purpose": "x " * 200, "grain": "bill"}
    assert len(ds.description(row)) <= 250
    assert ds.description({"purpose": "Bills.", "grain": "bill"}) == "Bills. One row per bill."


def test_package_carries_datasource_folders_and_every_domain():
    rows = ds.parse_manifest(MANIFEST)
    pkg = ds.build_package(rows, {r["file"]: SCHEMA for r in rows}, _ds_zip(), "Origin_DEV_DS", "Origin_DEV",
                           "/SmartCity/Report/Origin_BA_2_0", "Origin BA 2.0")
    z = zipfile.ZipFile(io.BytesIO(pkg)); names = set(z.namelist())
    assert "resources/DataSource/Origin_DEV_DS.xml" in names
    assert "<label>Origin BA 2.0</label>" in z.read("resources/SmartCity/Report/Origin_BA_2_0/.folder.xml").decode()
    assert "<label>Billing and Rates</label>" in z.read("resources/SmartCity/Report/Origin_BA_2_0/Domains/Billing_and_Rates/.folder.xml").decode()
    dom = z.read("resources/SmartCity/Report/Origin_BA_2_0/Domains/Meter_Operations/On_Off_History___Domain.xml").decode()
    assert "<label>On/Off History - Domain</label>" in dom and "<uri>/DataSource/Origin_DEV_DS</uri>" in dom
    assert z.read("resources/SmartCity/Report/Origin_BA_2_0/Domains/Billing_and_Rates/Bill___Domain_files/schema.data").decode() == SCHEMA
    idx = z.read("index.xml").decode()
    assert 'name="rootTenantId" value="Origin_DEV"' in idx
    assert idx.count("<resource>") == 1 + len(rows)   # the datasource and each domain; folders come with them


def test_a_schema_bound_elsewhere_is_refused():
    rows = ds.parse_manifest(MANIFEST)
    try:
        ds.build_package(rows, {r["file"]: SCHEMA.replace("Origin_DEV_DS", "Ellensburg_DS") for r in rows}, _ds_zip(),
                         "Origin_DEV_DS", "Origin_DEV", "/SmartCity/Report/Origin_BA_2_0", "Origin BA 2.0")
    except SystemExit as e:
        assert "Origin_DEV_DS" in str(e)
    else:
        raise AssertionError("a schema bound to another datasource was packaged")
