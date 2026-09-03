#!/usr/bin/env python3
"""Build Newark REP8 staging-table Domain import ZIP.

Canonical schema: domains/manual_imports/newark_rep8_aged_balance_domain/schema.reference.xml
Validated on Newark1 JRS import 2026-09-02.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = REPO_ROOT / "domains/manual_imports/newark_rep8_aged_balance_domain"
DOMAIN_NAME = "Newark_REP8_Aged_Balance___Domain"
FOLDER = "/SmartCity/Report/Workstreams/Debt_Management"
DOMAIN_URI = f"{FOLDER}/{DOMAIN_NAME}"
SCHEMA_REFERENCE = OUT_ROOT / "schema.reference.xml"


def validate_schema(path: Path) -> None:
    validator = REPO_ROOT / "scripts/jaspersoft/validate_domain_schema.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"schema validation failed:\n{result.stdout}\n{result.stderr}")


def build_domain_xml() -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<semanticLayerDataSource exportedWithPermissions="true">
    <folder>{FOLDER}</folder>
    <name>{DOMAIN_NAME}</name>
    <version>1</version>
    <label>Newark REP8 Aged Balance - Domain</label>
    <description>Flat domain over JRS2C2M.REP8_AGED_BALANCE nightly staging (account grain).</description>
    <creationDate>2026-09-02T21:15:00.000Z</creationDate>
    <updateDate>2026-09-02T21:30:00.000Z</updateDate>
    <schema>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="schema.data" xsi:type="fileResource">
            <folder>{FOLDER}/{DOMAIN_NAME}_files</folder>
            <name>schema</name>
            <version>1</version>
            <label>schema</label>
            <description>schema</description>
            <creationDate>2026-09-02T21:15:00.000Z</creationDate>
            <updateDate>2026-09-02T21:30:00.000Z</updateDate>
            <fileType>xml</fileType>
        </localResource>
    </schema>
    <dataSource>
        <alias>Newark1_DS</alias>
        <dataSourceReference>
            <uri>/DataSource/Newark1_DS</uri>
        </dataSourceReference>
    </dataSource>
</semanticLayerDataSource>
"""


def write_zip(staging: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging).as_posix())


def main() -> int:
    if not SCHEMA_REFERENCE.is_file():
        raise SystemExit(f"Missing canonical schema: {SCHEMA_REFERENCE}")

    schema_path = OUT_ROOT / f"{DOMAIN_NAME}_files" / "schema.data"
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SCHEMA_REFERENCE, schema_path)
    validate_schema(schema_path)

    domain_path = OUT_ROOT / f"{DOMAIN_NAME}.xml"
    domain_path.write_text(build_domain_xml(), encoding="utf-8")

    staging = OUT_ROOT / "_import_staging"
    if staging.exists():
        shutil.rmtree(staging)

    res = staging / "resources" / "SmartCity" / "Report" / "Workstreams" / "Debt_Management"
    res.mkdir(parents=True, exist_ok=True)
    shutil.copy2(domain_path, res / f"{DOMAIN_NAME}.xml")
    files_dir = res / f"{DOMAIN_NAME}_files"
    files_dir.mkdir(exist_ok=True)
    shutil.copy2(schema_path, files_dir / "schema.data")

    folder_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<folder exportedWithPermissions="true">
    <folder>{FOLDER}</folder>
    <name>Debt_Management</name>
    <version>0</version>
    <label>Debt Management</label>
    <description></description>
    <creationDate>2026-09-02T21:15:00.000Z</creationDate>
    <updateDate>2026-09-02T21:30:00.000Z</updateDate>
    <permission>
        <permissionMask>1</permissionMask>
    </permission>
</folder>
"""
    (res / ".folder.xml").write_text(folder_xml, encoding="utf-8")

    (staging / "index.xml").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<export>
  <module id="repositoryResources">
    <resource>{DOMAIN_URI}</resource>
  </module>
  <property name="pathProcessorId" value="zip"/>
</export>
""",
        encoding="utf-8",
    )

    zip_path = OUT_ROOT / "Newark_REP8_Aged_Balance_Domain_client_import.zip"
    write_zip(staging, zip_path)

    print(f"Canonical schema: {SCHEMA_REFERENCE}")
    print(f"Wrote schema: {schema_path}")
    print(f"Wrote import zip: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
