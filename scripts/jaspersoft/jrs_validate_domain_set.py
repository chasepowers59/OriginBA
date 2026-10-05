#!/usr/bin/env python3
"""Prove an imported domain set on one org: each domain matches its generated definition, returns its canvas's
own row count, and every field executes. Read-only on the server and on the warehouse.

Three checks per domain under <root>/Domains:
  1. the server's fields (Ad Hoc metadata) equal the generated XML: none missing, extra or relabelled, same folders;
  2. a CountAll on the grain key (the contract's first column; CountAll skips blanks, so any other field can
     under-count) equals select count(*) from the canvas's BI view in the client's warehouse;
  3. every field executes, 40 at a time, one row each.

    scripts/jaspersoft/jrs.sh jrs_validate_domain_set.py --env test --org Origin_DEV \\
        --set-dir <generated set> --client ellensburg [--root /SmartCity/Report/Origin_BA_2_0] [--skip-fields]

The warehouse side uses originba_dbt (ORIGINBA_DBT_DIR, default ~/originba_dbt): its reporting contract for the
grain keys and its connect helper for the counts (credentials from ORIGINBA_ENV_FILE, default this repo's .env). Writes backups/jaspersoft/domain_validation/<run>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
CHUNK = 40


def generated_items(xml_text: str) -> dict[str, tuple[str, str]]:
    """item id -> (folder label, item label) from a generated domain schema."""
    root = ET.fromstring(xml_text)
    return {it.get("id"): (g.get("label"), it.get("label"))
            for g in root.find(f"{NS}itemGroups").findall(f"{NS}itemGroup") for it in g.iter(f"{NS}item")}


def view_for(file: str) -> str:
    return "RPT_" + file.removeprefix("originba_").removesuffix("_domain.xml").upper() + "_BI"


def differences(want: dict, got: dict) -> dict[str, list[str]]:
    return {"missing": sorted(set(want) - set(got)), "extra": sorted(set(got) - set(want)),
            "relabelled": sorted(k for k in set(want) & set(got) if want[k] != got[k])}


def grain_item(got: dict[str, tuple[str, str]], grain_column: str) -> str | None:
    """The item for the grain key's BI column (ids are <role prefix>_<BI column>)."""
    return next((k for k in got if k.split("_", 1)[-1] == grain_column), None)


def count_from(body: str | bytes) -> int:
    return int(float(json.loads(body)["dataset"]["rows"][0][0]))


def chunks(fields: list[str]):
    for k in range(0, len(fields), CHUNK):
        yield fields[k:k + CHUNK]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--set-dir", type=pathlib.Path, required=True); ap.add_argument("--client", required=True)
    ap.add_argument("--root", default="/SmartCity/Report/Origin_BA_2_0"); ap.add_argument("--skip-fields", action="store_true")
    a = ap.parse_args()
    import jrs_import_domain as one
    import jrs_import_domain_set as ids
    import jrs_promote
    import jrs_run_sweep as sw
    dbt = pathlib.Path(os.environ.get("ORIGINBA_DBT_DIR", pathlib.Path.home() / "originba_dbt"))
    sys.path.insert(0, str(dbt / "scripts"))
    from build_portal_catalog import load_contracts
    from oracle_source_drift import connect
    from bi_names import safe_columns
    contracts = load_contracts(dbt)
    con = connect(os.environ.get("ORIGINBA_ENV_FILE", str(REPO / ".env")), a.client)
    con.call_timeout = 900_000
    cur = con.cursor()
    one._scope(a.env, a.org)

    rows = ids.parse_manifest((a.set_dir / "README.md").read_text())
    by_name = {ids.resource_name(r["label"]): r for r in rows}
    code, body, _ = sw._http("/rest_v2/resources?folderUri=" + urllib.parse.quote(f"{a.root}/Domains")
                             + "&type=semanticLayerDataSource&recursive=true&limit=500")
    uris = sorted(r["uri"] for r in json.loads(body)["resourceLookup"]) if code == 200 else []
    on_server = {u.rsplit("/", 1)[-1]: u for u in uris}
    results, problems = [], 0
    for name in sorted(set(by_name) | set(on_server)):
        r, uri = by_name.get(name), on_server.get(name)
        if not r or not uri:
            print(f"FAIL {name}: {'not on the server' if r else 'on the server, not in the set'}")
            results.append({"domain": name, "ok": False, "why": "missing" if r else "extra"}); problems += 1
            continue
        want = generated_items((a.set_dir / r["file"]).read_text(encoding="utf-8"))
        code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=180)
        meta = json.loads(body)
        levels = jrs_promote.domain_levels(meta)
        level_of = {i["id"]: lv["id"] for lv in levels for i in lv.get("items", [])}
        got = {i["id"]: (lv.get("label") or lv["id"], i.get("label")) for lv in levels for i in lv.get("items", [])}
        diff = differences(want, got)
        canvas = view_for(r["file"]).removesuffix("_BI").lower()
        cols = [c["name"] for c in contracts[canvas]["columns"]]
        key = grain_item(got, safe_columns(cols)[cols[0]])
        q = {"select": {"aggregations": [{"id": "n", "fieldRef": f"{level_of[key]}.{key}", "aggregateFunction": "CountAll"}]}}
        c, b, _ = sw._http("/rest_v2/queryExecutions", "POST",
                           json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode(),
                           "application/execution.multiLevelQuery+json", "application/flatData+json", 600)
        jrs_rows = count_from(b) if c == 200 else None
        cur.execute(f"select count(*) from ORIGINBA_REPORTING.{view_for(r['file'])}")
        ora_rows = cur.fetchone()[0]
        bad_chunks = []
        if not a.skip_fields:
            fields = [f"{level_of[k]}.{k}" for k in got]
            for chunk in chunks(fields):
                payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": {"select": {
                    "fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(chunk)]}}}).encode()
                c2, b2, _ = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=1", "POST", payload,
                                     "application/execution.multiLevelQuery+json", "application/flatData+json", 300)
                if c2 != 200:
                    bad_chunks.append(sw._message(b2)[:160])
        ok = not any(diff.values()) and jrs_rows == ora_rows and not bad_chunks
        problems += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {len(got)} fields ({', '.join(f'{k} {len(v)}' for k, v in diff.items())}); "
              f"rows {jrs_rows} / {ora_rows:,}{'; failing field chunks ' + str(len(bad_chunks)) if bad_chunks else ''}",
              flush=True)
        results.append({"domain": name, "ok": ok, "fields": len(got), **diff, "jaspersoft_rows": jrs_rows,
                        "warehouse_rows": ora_rows, "failing_field_chunks": bad_chunks})
    out = REPO / "backups" / "jaspersoft" / "domain_validation" / f"{a.env}_{a.org}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1, default=str))
    print(f"{len(results)} domains, {problems} problem(s) -> {out.relative_to(REPO)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
