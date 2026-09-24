#!/usr/bin/env python3
"""Apply a schema patch to an org's OWN domain in place, as root, with proof.

    scripts/jaspersoft/jrs.sh jrs_domain_patch_apply.py --env test --org Origin_DEV \\
        --domain /SmartCity/Report/Standard_Offering/Debt_Management/Severance_Process/Severance_Process___Domain \\
        --patch patch_severance_domain [--dry-run] [--i-mean-prod]

The patch module exposes patch_schema(xml) -> xml and SETS (the item groups it adds). Order, each
step its own proof: 1. export the domain (the rollback) 2. patch THAT org's schema (its own
datasource id) and validate 3. PUT the schema with its current version 4. read it back byte-equal
5. /domains/<uri>/metadata lists every added set 6. every Ad Hoc view bound to the domain still
executes 7. a flat query of the added items answers.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import domain_schema  # noqa: E402
import jrs_debug as dbg  # noqa: E402
import jrs_inventory as inv  # noqa: E402
import jrs_run_sweep as sw  # noqa: E402
from jrs_promote import org_root  # noqa: E402

REPO = HERE.parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True); ap.add_argument("--domain", required=True)
    ap.add_argument("--patch", required=True, help="module under scripts/jaspersoft with patch_schema() and SETS")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    ap.add_argument("--restore", type=pathlib.Path, metavar="schema.before.xml", help="PUT this saved pre-patch schema back (the rollback); the patch's sets must then be absent")
    a = ap.parse_args()
    if a.env == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("prod needs --i-mean-prod")
    patch = importlib.import_module(a.patch)
    os.environ["JRS_ENV"] = a.env; sw._AUTH.header = None
    uri = org_root(a.org) + a.domain
    if a.restore:
        return restore(uri, a.restore.read_text(encoding="utf-8"), patch, f"{a.env}:{a.org}{a.domain}")
    work = REPO / "backups" / "jaspersoft" / "domain_patch" / f"{a.env}_{a.org}_{a.domain.rsplit('/', 1)[-1]}_{time.strftime('%Y%m%d-%H%M%S')}"
    work.mkdir(parents=True, exist_ok=True)
    (work / "before.zip").write_bytes(inv.export_zip([uri]))
    before = dbg.get_file(uri + "_files/schema").decode("utf-8")
    (work / "schema.before.xml").write_text(before)
    print(f"1. exported {(work / 'before.zip').relative_to(REPO)} (the rollback); schema {len(before):,} bytes")

    patched = patch.patch_schema(before)
    out = work / "schema.patched.xml"; out.write_text(patched)
    lost = domain_schema.additions_only(before, patched)
    if lost:
        raise SystemExit("2. the patch is not purely additive; refused. Lost or altered:\n   " + "\n   ".join(lost[:20]))
    r = subprocess.run([sys.executable, str(HERE / "validate_domain_schema.py"), str(out)], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"2. validator refused the patched schema:\n{r.stdout}{r.stderr}")
    print(f"2. patched, validated, ADDITIVE ONLY (every existing id, label, join and expression unchanged): +{len(patched) - len(before):,} bytes, sets {[s[0] for s in patch.SETS]}")
    if a.dry_run:
        print("3. dry run: nothing written"); return 0

    if dbg.domain_apply(uri, str(out)) != 0:
        raise SystemExit("3. PUT failed; the export above restores the org")
    after = dbg.get_file(uri + "_files/schema").decode("utf-8")
    if after != patched:
        raise SystemExit("4. read-back differs from what was written")
    print("3. schema PUT with its version\n4. read back byte-equal")

    code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=300)
    if code != 200:
        raise SystemExit(f"5. metadata {code}: {sw._message(body)[:300]}")
    levels = {l["id"]: l for l in json.loads(body)["rootLevel"]["subLevels"]}
    missing = [s[0] for s in patch.SETS if s[0] not in levels]
    if missing:
        raise SystemExit(f"5. metadata lacks the added sets {missing}")
    print(f"5. metadata lists {len(levels)} sets including {[s[0] for s in patch.SETS]}")

    code, body, _ = sw._http(f"/rest_v2/resources?type=adhocDataView&q=&folderUri={urllib.parse.quote(org_root(a.org))}&recursive=true&limit=1000", timeout=120)
    views = [v["uri"] for v in json.loads(body).get("resourceLookup", []) if code == 200]
    bound = []
    for v in views:
        c, b, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(v)}?expanded=false", timeout=60)
        if c == 200 and uri in b.decode("utf-8", "replace"):
            bound.append(v)
    bad = []
    for v in bound:
        res = sw.run_view(v, 600)
        print(f"   view {v[len(org_root(a.org)):]}: {res['outcome']} {res.get('rows', '')}")
        if res["outcome"] not in ("ok", "empty"):
            bad.append(v)
    print(f"6. {len(bound)} bound views executed, {len(bad)} failed")

    items = [f"{sid}.{i}" for sid, _, its in patch.SETS for i, _, _ in its][:10]
    payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": {"select": {"fields": [{"id": f"f{n}", "field": f} for n, f in enumerate(items)]}}}).encode()
    code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=5", "POST", payload, "application/execution.multiLevelQuery+json", "application/flatData+json", 600)
    if code != 200:
        raise SystemExit(f"7. probe of the added items: {code} {sw._message(body)[:300]}")
    print(f"7. probe of {len(items)} added items answers {json.loads(body).get('totalCounts')} rows in {dt:.1f}s")
    print(("PASS" if not bad else "CHECK: a bound view failed; the export above restores the org") + f"  {a.env}:{a.org}{a.domain}")
    return 1 if bad else 0


def restore(uri: str, before: str, patch, what: str) -> int:
    """Roll a patched domain back to its saved schema: PUT, read back byte-equal, metadata without the sets."""
    live = dbg.get_file(uri + "_files/schema").decode("utf-8")
    if live == before:
        print(f"already the pre-patch schema, nothing to do  {what}"); return 0
    if dbg.domain_apply(uri, str(_tmp(before))) != 0:
        raise SystemExit("restore PUT failed")
    if dbg.get_file(uri + "_files/schema").decode("utf-8") != before:
        raise SystemExit("restore read-back differs from the saved schema")
    code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=300)
    levels = {l["id"] for l in json.loads(body)["rootLevel"]["subLevels"]} if code == 200 else set()
    left = [s[0] for s in patch.SETS if s[0] in levels]
    if left:
        raise SystemExit(f"restored schema but metadata still lists {left}")
    print(f"RESTORED  {what}: schema back to the saved pre-patch bytes, {len(levels)} sets, none of the patch's")
    return 0


def _tmp(text: str) -> pathlib.Path:
    p = REPO / "backups" / "jaspersoft" / "domain_patch" / f"restore_{time.strftime('%Y%m%d-%H%M%S')}.xml"
    p.write_text(text, encoding="utf-8"); return p


if __name__ == "__main__":
    sys.exit(main())
