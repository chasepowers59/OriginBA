#!/usr/bin/env python3
"""Build the JasperReports Server IMPORT ZIP for the finance report pack.

The first bundle (a manifest + loose files) was refused: "provided zip file is not valid
JasperReports Server export file" (DEV, 2026-09-17). A JRS import is the server's own export
shape, learned and verified in originba-letterprint (jasperserver/tools/build_import_bundle.py,
imported on an 8.1.0 PRO tenant) and on Newark REP8:

    index.xml                                   LAST entry in the zip; lists the import roots
    favorites/                                  empty directory entry, as a real export carries
    resources/<each folder>/.folder.xml         one per folder on the path, parent + name
    resources/<folder>/<unit>.xml               <reportUnit>: mainReport, inputControls (local),
                                                resources (the subreport, local jrxml), dataSource
    resources/<folder>/<unit>_files/main_jrxml.data       the main JRXML
    resources/<folder>/<unit>_files/<sub>.data            the subreport JRXML, resource name <sub>
                                                          (the main references "repo:<sub>")

Tenant-relative: no rootTenantId, so the same zip imports into DEV or inside a client org.
The datasource is BOUND on each unit (--datasource, default /DataSource/Origin_DEV_DS) and
must already exist on the target; pass the client's (/DataSource/Newark1_DS) for a tenant.
jsVersion is measured ("8.1.0 PRO" from deploy/jaspersoft_datasources/canonical/Origin_DEV_DS_export.zip),
never guessed. keyalias/encrypted are omitted: a content-only bundle needs neither
(letterprint, verified); if a server ever answers "not valid export file" to THIS shape, copy
both from a real export of that tenant.

    python3 scripts/jaspersoft/build_finance_pack_jrs_import.py [--datasource /DataSource/X_DS] [--out ZIP]
"""
from __future__ import annotations

import argparse
import datetime
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_sql_report_pack as g  # noqa: E402

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
JS_VERSION = "8.1.0 PRO"
# JRS input-control dataType.type: 1 text, 2 number, 3 date, 4 datetime; inputControl.type 2 = single value
DATATYPE = {"singleValueText": 1, "singleValueNumber": 2, "singleValueDate": 3}


def folder_xml(parent: str, name: str) -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<folder exportedWithPermissions="false">\n'
            f"    <parent>{parent}</parent>\n    <name>{name}</name>\n    <label>{name}</label>\n"
            f"    <creationDate>{STAMP}</creationDate>\n    <updateDate>{STAMP}</updateDate>\n</folder>\n")


def input_control(unit_folder: str, ic: dict) -> str:
    dt = DATATYPE[ic["type"]]
    return f'''    <inputControl>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" xsi:type="inputControl">
            <folder>{unit_folder}_files</folder>
            <name>{ic["id"]}</name>
            <version>1</version>
            <label>{escape(ic["label"])}</label>
            <creationDate>{STAMP}</creationDate>
            <updateDate>{STAMP}</updateDate>
            <type>2</type>
            <mandatory>{"true" if ic["mandatory"] else "false"}</mandatory>
            <readOnly>false</readOnly>
            <visible>true</visible>
            <dataType>
                <localResource exportedWithPermissions="false" xsi:type="dataType">
                    <folder>{unit_folder}_files/{ic["id"]}_files</folder>
                    <name>myDatatype</name>
                    <version>0</version>
                    <label>myDatatype</label>
                    <creationDate>{STAMP}</creationDate>
                    <updateDate>{STAMP}</updateDate>
                    <type>{dt}</type>
                    <strictMin>false</strictMin>
                    <strictMax>false</strictMax>
                </localResource>
            </dataType>
        </localResource>
    </inputControl>
'''


def subreport_resource(unit_folder: str, name: str) -> str:
    return f'''    <resource>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="{name}.data" xsi:type="fileResource">
            <folder>{unit_folder}_files</folder>
            <name>{name}</name>
            <version>1</version>
            <label>{name}</label>
            <creationDate>{STAMP}</creationDate>
            <updateDate>{STAMP}</updateDate>
            <fileType>jrxml</fileType>
        </localResource>
    </resource>
'''


def report_unit(spec: g.Spec, folder: str, datasource: str) -> str:
    unit_folder = f"{folder}/{spec.name}"
    doc, _ = g.controls(spec)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<reportUnit exportedWithPermissions="false">
    <folder>{folder}</folder>
    <name>{spec.name}</name>
    <version>1</version>
    <label>{escape(spec.label)}</label>
    <description>{escape(spec.description)}</description>
    <creationDate>{STAMP}</creationDate>
    <updateDate>{STAMP}</updateDate>
    <mainReport>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="main_jrxml.data" xsi:type="fileResource">
            <folder>{unit_folder}_files</folder>
            <name>main_jrxml</name>
            <version>1</version>
            <label>Main jrxml</label>
            <creationDate>{STAMP}</creationDate>
            <updateDate>{STAMP}</updateDate>
            <fileType>jrxml</fileType>
        </localResource>
    </mainReport>
    <dataSource>
        <uri>{datasource}</uri>
    </dataSource>
{"".join(input_control(unit_folder, ic) for ic in doc["inputControls"])}{subreport_resource(unit_folder, spec.sub.name)}    <alwaysPromptControls>true</alwaysPromptControls>
    <controlsLayout>1</controlsLayout>
</reportUnit>
'''


def build(out_zip: Path, datasource: str) -> Path:
    files: dict[str, bytes] = {}
    folders: set[str] = set()
    for spec in g.SPECS:
        folder = g.FOLDERS[spec.name]
        parts = folder.strip("/").split("/")
        for i in range(len(parts)):
            folders.add("/" + "/".join(parts[: i + 1]))
        rel = folder.strip("/")
        files[f"resources/{rel}/{spec.name}.xml"] = report_unit(spec, folder, datasource).encode()
        files[f"resources/{rel}/{spec.name}_files/main_jrxml.data"] = (g.REPORTS / f"{spec.name}.jrxml").read_bytes()
        files[f"resources/{rel}/{spec.name}_files/{spec.sub.name}.data"] = (g.SUBS / f"{spec.sub.name}.jrxml").read_bytes()
    for f in sorted(folders):
        parent, name = f.rsplit("/", 1)
        files[f"resources/{f.strip('/')}/.folder.xml"] = folder_xml(parent or "/", name).encode()
    roots = sorted({g.FOLDERS[s.name] for s in g.SPECS})
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n<export><module id="repositoryResources">'
             + "".join(f"<folder>{r}</folder>" for r in roots)
             + '</module><module id="favorites"/><property name="pathProcessorId" value="zip"/>'
             f'<property name="jsVersion" value="{JS_VERSION}"/></export>\n')
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    out_zip.unlink(missing_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("favorites/"), b"")
        for name in sorted(files):
            z.writestr(name, files[name])
        z.writestr("index.xml", index)   # last: the importer reads the archive in order
    return out_zip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasource", default="/DataSource/Origin_DEV_DS")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    ds_slug = a.datasource.rsplit("/", 1)[-1]
    out = a.out or REPO / "deploy" / f"finance_pack_jrs_import_{ds_slug}.zip"
    z = build(out, a.datasource)
    with zipfile.ZipFile(z) as zf:
        print(f"{z.relative_to(REPO)}  ({len(zf.namelist())} entries, {z.stat().st_size // 1024} KB, datasource {a.datasource})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
