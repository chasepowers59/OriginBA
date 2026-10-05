#!/usr/bin/env python3
"""Import a generated domain set (originba_dbt `jaspersoft/domains/<target>/`) into one org, then prove
every domain opens and answers.

One package: the org's own datasource export (taken minutes before, so nothing is repointed), the
offering root, `Domains/<workstream>` with the Standard Offering's own workstream folder names (from the
set's README manifest), and one domain per data set, named the Standard Offering way (`Bill___Domain`,
"Bill - Domain"). After the import, each domain's Ad Hoc metadata is read and a flat query of its root
set is executed, so "imported" means "opens and answers".

    scripts/jaspersoft/jrs.sh jrs_import_domain_set.py --env test --org Origin_DEV --ds Origin_DEV_DS \\
        --set-dir ~/originba_dbt/jaspersoft/domains/ellensburg_origin_dev \\
        --root /SmartCity/Report/Origin_BA_2_0 --root-label "Origin BA 2.0" [--dry-run]
"""
from __future__ import annotations

import argparse
import io
import json
import pathlib
import re
import sys
import time
import urllib.parse
import zipfile
from xml.sax.saxutils import escape

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
ROW = re.compile(r"^\| (?P<label>[^|]+?) \| `(?P<file>[^`]+)` \| `Domains/(?P<folder>[^`]+)` \| (?P<grain>[^|]*?) \| "
                 r"\d+ \| \d+ \| (?P<purpose>.*?) \|$")


def parse_manifest(text: str) -> list[dict]:
    return [{k: m.group(k).strip() for k in ("label", "file", "folder", "grain", "purpose")}
            for m in map(ROW.match, text.splitlines()) if m]


def resource_name(label: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_") + "___Domain"


def resource_label(label: str) -> str:
    return f"{label} - Domain"


def folder_label(folder: str) -> str:
    return folder.replace("_and_", " and ").replace("_", " ")


def description(row: dict) -> str:
    text = f"{row['purpose']} One row per {row['grain']}.".strip()
    return text if len(text) <= 250 else text[:247].rsplit(" ", 1)[0] + "..."


def _folder_xml(parent: str, name: str, label: str, desc: str, now: str) -> bytes:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<folder exportedWithPermissions="false">\n    <parent>{parent}</parent>\n'
            f'    <name>{name}</name>\n    <label>{escape(label)}</label>\n    <description>{escape(desc)}</description>\n'
            f'    <creationDate>{now}</creationDate>\n    <updateDate>{now}</updateDate>\n</folder>\n').encode()


def _domain_xml(folder: str, row: dict, ds: str, now: str) -> bytes:
    name = resource_name(row["label"])
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<semanticLayerDataSource exportedWithPermissions="false">
    <folder>{folder}</folder>
    <name>{name}</name>
    <version>0</version>
    <label>{escape(resource_label(row["label"]))}</label>
    <description>{escape(description(row))}</description>
    <creationDate>{now}</creationDate>
    <updateDate>{now}</updateDate>
    <schema>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="schema.data" xsi:type="fileResource">
            <folder>{folder}/{name}_files</folder>
            <name>schema</name>
            <version>0</version>
            <label>schema</label>
            <description>schema</description>
            <creationDate>{now}</creationDate>
            <updateDate>{now}</updateDate>
            <fileType>xml</fileType>
        </localResource>
    </schema>
    <dataSource>
        <alias>{ds}</alias>
        <dataSourceReference>
            <uri>/DataSource/{ds}</uri>
        </dataSourceReference>
    </dataSource>
</semanticLayerDataSource>
'''.encode()


def build_package(rows: list[dict], schemas: dict[str, str], ds_zip: bytes, ds: str, org: str, root: str, root_label: str) -> bytes:
    bad = [r["file"] for r in rows if f'datasourceId="{ds}"' not in schemas[r["file"]]]
    if bad:
        raise SystemExit(f"schemas not bound to datasource id {ds} (generate the set with --datasource {ds}): {bad[:3]}")
    dsz = zipfile.ZipFile(io.BytesIO(ds_zip)); idx = dsz.read("index.xml").decode()
    prop = lambda k: re.search(rf'name="{k}" value="([^"]+)"', idx).group(1)
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    parts = root.strip("/").split("/")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in dsz.namelist():
            if n.startswith("resources/DataSource/") and not n.endswith("/"):
                z.writestr(n, dsz.read(n))
        for i in range(1, len(parts)):   # existing ancestors, written as they are (label = name)
            z.writestr("resources/" + "/".join(parts[:i]) + "/.folder.xml",
                       _folder_xml("/" + "/".join(parts[:i - 1]) if i > 1 else "/", parts[i - 1], parts[i - 1], "", now))
        z.writestr(f"resources{root}/.folder.xml", _folder_xml("/" + "/".join(parts[:-1]), parts[-1], root_label,
                   "One domain per reporting data set: each a single grain, its fields in folders by the C2M object they describe.", now))
        z.writestr(f"resources{root}/Domains/.folder.xml", _folder_xml(root, "Domains", "Domains",
                   "Build Ad Hoc views from these. Filed by the Standard Offering's workstreams.", now))
        for ws in sorted({r["folder"] for r in rows}):
            z.writestr(f"resources{root}/Domains/{ws}/.folder.xml", _folder_xml(f"{root}/Domains", ws, folder_label(ws), "", now))
        for r in rows:
            folder = f"{root}/Domains/{r['folder']}"; name = resource_name(r["label"])
            z.writestr(f"resources{folder}/{name}.xml", _domain_xml(folder, r, ds, now))
            z.writestr(f"resources{folder}/{name}_files/schema.data", schemas[r["file"]].encode())
        res = "".join(f"<resource>{root}/Domains/{r['folder']}/{resource_name(r['label'])}</resource>" for r in rows)
        z.writestr("index.xml", (f'<?xml version="1.0" encoding="UTF-8"?>\n<export><property name="keyalias" value="{prop("keyalias")}"/>'
                                 f'<module id="repositoryResources"><resource>/DataSource/{ds}</resource>{res}</module>'
                                 f'<module id="favorites"/><property name="pathProcessorId" value="zip"/>'
                                 f'<property name="rootTenantId" value="{org}"/><property name="jsVersion" value="{prop("jsVersion")}"/>'
                                 f'<property name="encrypted" value="{prop("encrypted")}"/></export>').encode())
    return out.getvalue()


def verify(uri: str) -> dict:
    """Ad Hoc metadata (what the designer lists) and a flat query of the root set's first items."""
    import jrs_promote
    import jrs_run_sweep as sw
    code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=180)
    if code != 200:
        return {"uri": uri, "ok": False, "why": f"metadata {code} {sw._message(body)[:200]}"}
    meta = json.loads(body); levels = jrs_promote.domain_levels(meta)
    probe = jrs_promote.probe_fields(meta)
    q = {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(probe)]}}
    payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode()
    code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=5", "POST", payload,
                              "application/execution.multiLevelQuery+json", "application/flatData+json", 300)
    if code != 200:
        return {"uri": uri, "ok": False, "folders": [l["id"] for l in levels], "why": f"query {code} {sw._message(body)[:200]}"}
    j = json.loads(body)
    return {"uri": uri, "ok": True, "folders": [l.get("label") or l["id"] for l in levels],
            "items": sum(len(l.get("items", [])) for l in levels), "rows": j.get("totalCounts"), "seconds": round(dt, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True); ap.add_argument("--ds", required=True)
    ap.add_argument("--set-dir", type=pathlib.Path, required=True)
    ap.add_argument("--root", required=True); ap.add_argument("--root-label", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.env == "prod":
        raise SystemExit("this tool writes test and internal orgs only; prod goes through jrs_promote_test_to_prod.py")
    import jrs_import_domain as one
    import jrs_inventory as inv
    import jrs_run_sweep as sw
    rows = parse_manifest((a.set_dir / "README.md").read_text())
    schemas = {r["file"]: (a.set_dir / r["file"]).read_text(encoding="utf-8") for r in rows}
    one._scope(a.env, a.org)
    pkg = build_package(rows, schemas, inv.export_zip([f"/DataSource/{a.ds}"]), a.ds, a.org, a.root, a.root_label)
    work = REPO / "backups" / "jaspersoft" / "domain_import" / f"{a.env}_{a.org}_set_{time.strftime('%Y%m%d-%H%M%S')}"
    work.mkdir(parents=True, exist_ok=True); (work / "import.zip").write_bytes(pkg)
    print(f"1. package {work.relative_to(REPO) / 'import.zip'} ({len(pkg):,} bytes): {a.ds} + {len(rows)} domains under {a.root}/Domains")
    if a.dry_run:
        print("2. dry run: nothing imported"); return 0
    one._scope(a.env, a.org)
    code, body, _ = sw._http("/rest_v2/import?update=true&skipUserUpdate=true", "POST", pkg, "application/zip")
    if code not in (200, 201):
        raise SystemExit(f"import request: {code} {sw._message(body)[:300]}")
    tid = json.loads(body)["id"]
    while True:
        code, body, _ = sw._http(f"/rest_v2/import/{tid}/state"); st = json.loads(body)
        if st.get("phase") in ("finished", "failed"):
            break
        time.sleep(3)
    if st.get("phase") != "finished" or st.get("warnings"):
        raise SystemExit(f"2. import did not complete cleanly: {json.dumps(st)[:800]}")
    print("2. import finished, no warnings")
    results = [verify(f"{a.root}/Domains/{r['folder']}/{resource_name(r['label'])}") for r in rows]
    (work / "verify.json").write_text(json.dumps(results, indent=2))
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["uri"] + (f"  {r['items']} fields, {len(r['folders'])} folders, {r['rows']} rows, {r['seconds']}s"
                                                              if r["ok"] else f"  {r['why']}"))
    bad = [r for r in results if not r["ok"]]
    print(f"3. {len(results) - len(bad)}/{len(results)} domains open and answer")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
