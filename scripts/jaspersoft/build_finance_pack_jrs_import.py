#!/usr/bin/env python3
"""Build the JasperReports Server IMPORT ZIP for the finance report pack.

Two shapes were refused or ignored on DEV (2026-09-17) before this one: a manifest bundle
("not a valid JasperReports Server export file") and a content-only export without the
datasource or keyalias ("imported fine" -- and imported NOTHING: the server skips a package
it cannot pair with a key and a datasource it can resolve inside the batch). The shape that
lands is the one Newark REP8 and the Standard Offering pipeline use, and the repo's own
verifier (scripts/jaspersoft/verify_standard_offering_tenant_import.py) encodes:

    index.xml           LAST entry; keyalias FIRST, then <module id="repositoryResources"> with the
                        datasource <resource> and the import <folder>s, <module id="favorites"/>,
                        pathProcessorId, jsVersion, encrypted -- keyalias/encrypted/jsVersion are
                        COPIED from a real export of the target tenant, never invented
    favorites/          empty, deflated directory entry
    resources/DataSource/.folder.xml + <DS>.xml   the datasource resource itself, verbatim from
                        that same export (the unit's <dataSource><uri> must resolve in the batch)
    resources/<folder>/.folder.xml                one per folder on the path
    resources/<folder>/<unit>.xml                 <reportUnit>: mainReport, dataSource, local
                                                  inputControls, the subreport as a local jrxml
                                                  resource named what the main's repo:<name> says
    resources/<folder>/<unit>_files/main_jrxml.data, <sub>.data

Tenant-relative (no rootTenantId): import from INSIDE the tenant's Repository.

    python3 scripts/jaspersoft/build_finance_pack_jrs_import.py                       # DEV (Origin_DEV_DS)
    python3 scripts/jaspersoft/build_finance_pack_jrs_import.py --datasource Newark1_DS \
        --datasource-export deploy/jaspersoft_datasources/clients/Newark1_DS
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
CANONICAL = REPO / "deploy" / "jaspersoft_datasources" / "canonical"
CLIENTS = REPO / "deploy" / "jaspersoft_datasources" / "clients"
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


def load_datasource_export(ds: str, export: Path | None) -> tuple[dict[str, bytes], dict[str, str]]:
    """The DataSource resource files and the index metadata (keyalias, encrypted, jsVersion) of a
    REAL export of the target tenant. Default: the canonical DEV export for Origin_DEV_DS, the
    client's folder under deploy/jaspersoft_datasources/clients/ otherwise."""
    import xml.etree.ElementTree as ET
    if export is None:
        export = CANONICAL / f"{ds}_export.zip" if (CANONICAL / f"{ds}_export.zip").exists() else CLIENTS / ds
    wanted = {"index.xml", "resources/DataSource/.folder.xml", f"resources/DataSource/{ds}.xml"}
    files: dict[str, bytes] = {}
    if export.is_file():
        with zipfile.ZipFile(export) as zf:
            for n in zf.namelist():
                if n in wanted:
                    files[n] = zf.read(n)
    elif export.is_dir():
        for n in wanted:
            if (export / n).exists():
                files[n] = (export / n).read_bytes()
    missing = wanted - set(files)
    if missing:
        raise SystemExit(f"datasource export {export} lacks {sorted(missing)}; export /DataSource/{ds} from the tenant first")
    meta = {p.get("name"): p.get("value") for p in ET.fromstring(files.pop("index.xml")).findall("property")}
    for k in ("keyalias", "encrypted", "jsVersion"):
        if not meta.get(k):
            raise SystemExit(f"{export}: index.xml carries no {k}; a real server export always does")
    return files, meta


def build(out_zip: Path, datasource: str, export: Path | None = None) -> Path:
    ds_files, meta = load_datasource_export(datasource, export)
    ds_uri = f"/DataSource/{datasource}"
    files: dict[str, bytes] = dict(ds_files)
    folders: set[str] = set()
    for spec in g.SPECS:
        folder = g.FOLDERS[spec.name]
        parts = folder.strip("/").split("/")
        for i in range(len(parts)):
            folders.add("/" + "/".join(parts[: i + 1]))
        rel = folder.strip("/")
        files[f"resources/{rel}/{spec.name}.xml"] = report_unit(spec, folder, ds_uri).encode()
        files[f"resources/{rel}/{spec.name}_files/main_jrxml.data"] = (g.REPORTS / f"{spec.name}.jrxml").read_bytes()
        files[f"resources/{rel}/{spec.name}_files/{spec.sub.name}.data"] = (g.SUBS / f"{spec.sub.name}.jrxml").read_bytes()
    for f in sorted(folders):
        parent, name = f.rsplit("/", 1)
        files[f"resources/{f.strip('/')}/.folder.xml"] = folder_xml(parent or "/", name).encode()
    roots = sorted({g.FOLDERS[s.name] for s in g.SPECS})
    # the exact layout of a server export: keyalias first, resources before folders inside the
    # module, favorites module, then the remaining properties; compact, no self-closing spaces
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             f'<export><property name="keyalias" value="{meta["keyalias"]}"/>'
             f'<module id="repositoryResources"><resource>{ds_uri}</resource>'
             + "".join(f"<folder>{r}</folder>" for r in roots)
             + '</module><module id="favorites"/><property name="pathProcessorId" value="zip"/>'
             f'<property name="jsVersion" value="{meta["jsVersion"]}"/>'
             f'<property name="encrypted" value="{meta["encrypted"]}"/></export>\n')
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    out_zip.unlink(missing_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        fav = zipfile.ZipInfo("favorites/"); fav.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(fav, b"")
        for name in sorted(files):
            z.writestr(name, files[name])
        z.writestr("index.xml", index)   # last: the importer reads the archive in order
    return out_zip


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datasource", default="Origin_DEV_DS", help="datasource NAME under /DataSource on the target tenant")
    ap.add_argument("--datasource-export", type=Path, default=None,
                    help="a real export of that datasource (zip or extracted dir); default: canonical/ or clients/<DS>/")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    ds = a.datasource.rsplit("/", 1)[-1]
    out = a.out or REPO / "deploy" / f"finance_pack_jrs_import_{ds}.zip"
    z = build(out, ds, a.datasource_export)
    with zipfile.ZipFile(z) as zf:
        print(f"{z.relative_to(REPO)}  ({len(zf.namelist())} entries, {z.stat().st_size // 1024} KB, datasource /DataSource/{ds})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
