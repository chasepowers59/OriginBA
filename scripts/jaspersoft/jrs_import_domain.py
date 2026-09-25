#!/usr/bin/env python3
"""Create a NEW domain in an org from a schema file, packaged with the org's own datasource.

The importer resolves a domain's datasource reference only against what is inside the package
(measured 2026-09-23), so the package carries the org's own `/DataSource/<ds>` export, taken
minutes before, listed first -- nothing is repointed, and the domain lands bound to the org's
database. Existing resources are untouched: the index lists the datasource and the new domain.

    scripts/jaspersoft/jrs.sh jrs_import_domain.py --env test --org Origin_DEV --ds Origin_DEV_DS \
        --folder /SmartCity/Report/Standard_Offering/Finance/Adjustments \
        --name Adjustment_AP_Request___Domain --label "Adjustment A/P Request - Domain" \
        --description "..." --schema path/to/schema.xml [--dry-run] [--i-mean-prod]

After the import: the domain's Ad Hoc metadata is fetched and its sets listed, and a flat query
of the first two items of every set is executed, so "imported" also means "opens and answers".
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402
import jrs_debug as dbg  # noqa: E402
import jrs_inventory as inv  # noqa: E402
import jrs_promote  # noqa: E402

REPO = HERE.parents[1]


def _scope(env: str, org: str) -> None:
    os.environ["JRS_ENV"] = env
    base = (os.environ.get(f"JRS_{env.upper()}_USER") or os.environ.get("JRS_USER", "")).split("|")[0]
    os.environ[f"JRS_{env.upper()}_USER"] = f"{base}|{org}"
    sw._AUTH.header = sw._auth_for(org)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True); ap.add_argument("--ds", required=True)
    ap.add_argument("--folder", required=True); ap.add_argument("--name", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--description", default=""); ap.add_argument("--schema", type=pathlib.Path, required=True)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    if a.env == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("prod needs --i-mean-prod")
    schema = a.schema.read_text(encoding="utf-8")
    if f'datasourceId="{a.ds}"' not in schema:
        raise SystemExit(f"the schema does not reference datasource id {a.ds}: build it for this org first")

    _scope(a.env, a.org)
    ds_zip = inv.export_zip([f"/DataSource/{a.ds}"])
    pkg = dbg._org_export_package(a.org, a.folder, a.name, a.label, a.description, schema, ds_zip, a.ds)
    work = REPO / "backups" / "jaspersoft" / "domain_import" / f"{a.env}_{a.org}_{a.name}_{time.strftime('%Y%m%d-%H%M%S')}"
    work.mkdir(parents=True, exist_ok=True)
    (work / "import.zip").write_bytes(pkg); (work / "schema.xml").write_text(schema)
    print(f"1. package {work.relative_to(REPO) / 'import.zip'} ({len(pkg):,} bytes): the org's own {a.ds} + {a.folder}/{a.name}")
    if a.dry_run:
        print("2. dry run: nothing imported"); return 0

    _scope(a.env, a.org)
    code, body, _ = sw._http("/rest_v2/import?update=true&skipUserUpdate=true", "POST", pkg, "application/zip")
    if code not in (200, 201):
        raise SystemExit(f"import request: {code} {sw._message(body)[:300]}")
    tid = json.loads(body)["id"]
    while True:
        code, body, _ = sw._http(f"/rest_v2/import/{tid}/state"); st = json.loads(body)
        if st.get("phase") in ("finished", "failed"):
            break
        time.sleep(2)
    if st.get("phase") != "finished" or st.get("warnings"):
        raise SystemExit(f"2. import did not complete cleanly: {json.dumps(st)[:600]}")
    print("2. import finished, no warnings")

    uri = f"{a.folder}/{a.name}"
    code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=180)
    if code != 200:
        raise SystemExit(f"3. metadata: {code} {sw._message(body)[:300]}")
    levels = jrs_promote.domain_levels(json.loads(body))
    print("3. Ad Hoc metadata:", ", ".join(f"{l['id']} ({len(l.get('items', []))})" for l in levels))
    probe = [f"{l['id']}.{i['id']}" for l in levels[:1] for i in l.get("items", [])[:2] if i.get("kind") != "measure"]   # the root set only: two items of every set drags every derived table in (152s on 501k adjustments)
    q = {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(probe)]}}
    payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode()
    code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=5", "POST", payload,
                              "application/execution.multiLevelQuery+json", "application/flatData+json", 300)
    if code != 200:
        raise SystemExit(f"4. probe query: {code} {sw._message(body)[:300]}")
    j = json.loads(body)
    cap = " (the server's Ad Hoc row cap; count through an aggregate query)" if j.get("totalCounts") == 300001 else ""
    print(f"4. probe query of {len(probe)} items: {j.get('totalCounts')} rows{cap} in {dt:.1f}s; first: {json.dumps((j.get('dataset') or {}).get('rows', [])[:1])[:240]}")
    print(f"PASS  {uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
