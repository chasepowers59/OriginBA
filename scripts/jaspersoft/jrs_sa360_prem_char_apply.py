#!/usr/bin/env python3
"""Give an org's Service Agreement 360 domain the premise-characteristics group, in place, with proof.

The patch is `build_service_agreement_360_prem_char_domain.patch_schema` applied to THAT ORG'S
OWN export (never Origin_DEV's file), so every table keeps the org's datasource id. Steps:

  1. export the domain from the org (backups/jaspersoft/domains/<stamp>/<env>_<org>_SA360.zip: the rollback)
  2. patch + validate the schema offline; skip if the group is already there
  3. PUT <domain>_files/schema with its current version (jrs_debug.domain_apply)
  4. prove: schema read back byte-equal; /rest_v2/domains/<uri>/metadata lists the group with its
     items (what the Ad Hoc designer shows); every Ad Hoc view in the org bound to the domain
     still executes; a flat query of the new items returns rows on the org's data

    python3 scripts/jaspersoft/jrs_sa360_prem_char_apply.py --env test --org Ellensburg --dry-run
    python3 scripts/jaspersoft/jrs_sa360_prem_char_apply.py --env prod --org Ellensburg --i-mean-prod

Filed under domains/manual_imports/service_agreement_360_prem_char/<org lower>_<env>/ afterwards.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.parse
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402
import jrs_debug as dbg  # noqa: E402
import build_service_agreement_360_prem_char_domain as builder  # noqa: E402

REPO = HERE.parents[1]
DOMAIN = "/SmartCity/Report/Standard_Offering/Customer_Operations/Service_Agreements/Service_Agreement___Domain"
GROUP = "CI_PREM_CHAR"
PROBE = ["CI_PREM_CHAR_PREM_ID", "CI_CHAR_TYPE_L_2_DESCR", "CI_PREM_CHAR_CHAR_VALUE", "CI_PREM_CHAR_CHAR_TYPE_FLG", "CI_PREM_CHAR_IS_CURRENT_SW"]


def _auth(env, org):
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)


def export_domain(env, org, out_zip: pathlib.Path) -> tuple[str, str]:
    cmd = [sys.executable, str(HERE / "jrs_repository.py"), "--env", env, "--org", org, "export", DOMAIN, "--out", str(out_zip)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False, env=os.environ)
    if r.returncode != 0 or not out_zip.exists():
        raise SystemExit(f"export failed: {r.stdout[-300:]} {r.stderr[-300:]}")
    return builder.extract_from_zip(out_zip)


def metadata_group(env, org) -> tuple[int | None, int]:
    _auth(env, org)
    c, b, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(DOMAIN)}/metadata", timeout=180)
    if c != 200:
        return c, 0
    found = []

    def walk(n):
        if isinstance(n, dict):
            if (n.get("name") or n.get("id")) == GROUP and ("elements" in n or "items" in n):
                found.append(len(n.get("elements") or n.get("items") or []))
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(json.loads(b))
    return c, (found[0] if found else 0)


def bound_views(env, org) -> list[str]:
    _auth(env, org)
    c, b, _ = sw._http("/rest_v2/resources?folderUri=/SmartCity&recursive=true&type=adhocDataView&limit=5000", timeout=180)
    uris = [i["uri"] for i in json.loads(b).get("resourceLookup", [])] if c == 200 else []

    def one(u):
        _auth(env, org)
        c2, d, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(u)}", timeout=90)
        try:
            return u, ((json.loads(d).get("dataSource") or {}).get("dataSourceReference") or {}).get("uri")
        except ValueError:
            return u, None
    with cf.ThreadPoolExecutor(6) as ex:
        return [u for u, ref in ex.map(one, uris) if ref == DOMAIN]


def probe_rows(env, org) -> tuple[int | None, int, str]:
    _auth(env, org)
    q = {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(PROBE)]}}
    payload = json.dumps({"dataSource": {"reference": {"uri": DOMAIN}}, "query": q}).encode()
    c, b, _ = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=5", "POST", payload,
                       "application/execution.multiLevelQuery+json", "application/flatData+json", timeout=300)
    if c != 200:
        return c, 0, sw._message(b)[:200]
    j = json.loads(b)
    return c, j.get("totalCounts", 0), json.dumps((j.get("dataset") or {}).get("rows", [])[:3])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    if a.env == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("prod needs --i-mean-prod")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    bdir = REPO / "backups" / "jaspersoft" / "domains" / stamp
    bdir.mkdir(parents=True, exist_ok=True)
    out_zip = bdir / f"{a.env}_{a.org}_SA360.zip"
    schema, wrapper = export_domain(a.env, a.org, out_zip)
    print(f"1. exported {out_zip.relative_to(REPO)} ({len(schema)} bytes of schema); this zip is the rollback")

    if builder.MARKER in schema:
        print("2. the group is already in this org's schema; nothing to apply")
        return 0
    patched = builder.patch_schema(schema)
    builder.check_wrapper_matches(patched, wrapper)
    patched_path = bdir / f"{a.env}_{a.org}_schema_patched.xml"
    patched_path.write_text(patched, encoding="utf-8")
    builder.validate_schema(patched_path)
    print(f"2. patched + validated ({len(schema)} -> {len(patched)} bytes), datasource {builder._datasource_id(patched)}")

    dbg.DRY["on"] = a.dry_run
    _auth(a.env, a.org)
    rc = dbg.domain_apply(DOMAIN, str(patched_path))
    if a.dry_run:
        print("3. dry run: nothing written"); return 0
    if rc:
        raise SystemExit("3. PUT failed; the org is unchanged")

    _auth(a.env, a.org)
    c, b, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(DOMAIN)}_files/schema", accept="application/octet-stream", timeout=120)
    same = c == 200 and b.decode("utf-8") == patched
    c2, n_items = metadata_group(a.env, a.org)
    views = bound_views(a.env, a.org)
    results = {u: sw.run_view(u, 180) for u in views}
    c3, rows, sample = probe_rows(a.env, a.org)
    print(f"4. schema read back byte-equal: {same}; Ad Hoc metadata lists {GROUP}: {n_items} items (HTTP {c2}); "
          f"bound views: {len(views)} -> {[r['outcome'] for r in results.values()]}; probe rows: {rows} (HTTP {c3}) {sample[:300]}")

    filed = REPO / "domains" / "manual_imports" / "service_agreement_360_prem_char" / f"{a.org.lower()}_{a.env}"
    builder.write_import_bundle(patched, wrapper, filed)
    shutil.rmtree(filed / "_import_staging", ignore_errors=True)
    (filed / "bound_views.json").write_text(json.dumps({u: r for u, r in results.items()}, indent=1))
    print(f"   filed under {filed.relative_to(REPO)}")
    ok = same and n_items >= 17 and all(r["outcome"] == "ok" for r in results.values()) and rows > 0
    print("PASS" if ok else "CHECK: one of the proofs did not hold; the export above restores the org")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
