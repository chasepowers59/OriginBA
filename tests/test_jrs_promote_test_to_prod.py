"""The test-to-prod package, built offline from real exports on disk: the datasource tree is
prod's own (byte-identical), the test host string is gone, the index names the datasource first
and the org. Uses the Origin_DEV Standard Offering export as the 'test' side and Fond du Lac
prod's datasource export as the 'prod' side -- the shapes are the same."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/jaspersoft"))
import jrs_promote_test_to_prod as pr  # noqa: E402

TEST = ROOT / "backups/jaspersoft/promotion/Origin_DEV_Standard_Offering_20260918-100136.zip"
PROD_DS = ROOT / "backups/jaspersoft/prod/20260918-071832/Fond_Du_Lac__DataSource.zip"
pytestmark = pytest.mark.skipif(not (TEST.exists() and PROD_DS.exists()), reason="needs the 2026-09-18 export zips (gitignored backups)")


def test_package_carries_prods_datasource_and_no_test_host():
    pkg = pr.build_package(TEST.read_bytes(), PROD_DS.read_bytes(), "Fond_Du_Lac", "/SmartCity/Report/Standard_Offering", "FondDuLac_DS")
    z = zipfile.ZipFile(io.BytesIO(pkg)); names = z.namelist()
    assert names[-1] == "index.xml"
    assert "resources/DataSource/FondDuLac_DS.xml" in names and "resources/DataSource/Origin_DEV_DS.xml" not in names
    assert not any(n.startswith("favorites/") for n in names)
    assert pr.verify_package(pkg, PROD_DS.read_bytes(), "FondDuLac_DS", ("smartcity-db-test", "10.13.4.91")) == []
    idx = z.read("index.xml").decode()
    assert 'rootTenantId" value="Fond_Du_Lac"' in idx and idx.index("/DataSource/FondDuLac_DS") < idx.index("<folder>")


def test_verify_catches_a_test_host_left_in_the_package():
    pkg = pr.build_package(TEST.read_bytes(), PROD_DS.read_bytes(), "Fond_Du_Lac", "/SmartCity/Report/Standard_Offering", "FondDuLac_DS")
    problems = pr.verify_package(pkg, PROD_DS.read_bytes(), "FondDuLac_DS", ("Standard_Offering",))   # a string that IS in the package
    assert problems and all("mentions the TEST host" in p for p in problems)


def test_verify_catches_a_swapped_datasource():
    pkg = pr.build_package(TEST.read_bytes(), PROD_DS.read_bytes(), "Fond_Du_Lac", "/SmartCity/Report/Standard_Offering", "FondDuLac_DS")
    other = io.BytesIO()
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("index.xml", zipfile.ZipFile(PROD_DS).read("index.xml")); z.writestr("resources/DataSource/FondDuLac_DS.xml", b"<x/>")
    assert any("not byte-identical" in p for p in pr.verify_package(pkg, other.getvalue(), "FondDuLac_DS", ()))
