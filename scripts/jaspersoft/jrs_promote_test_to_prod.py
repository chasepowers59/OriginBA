#!/usr/bin/env python3
"""Promote a client's folder from its TEST org to its PROD org, datasource untouched.

The two orgs carry a datasource of the SAME NAME (FondDuLac_DS on both) pointing at DIFFERENT
databases, and the server's folder export carries the datasource XML with it. Imported as-is,
the test export would repoint prod's datasource at the test database. So the package is
rebuilt: the test export minus its DataSource tree, plus prod's OWN datasource export taken
minutes earlier (re-saved byte-identical), index.xml listing the datasource first and the org's
rootTenantId, and a check that no test host string survives anywhere in the package.

Order, each step its own proof (see the jaspersoft-server-operations skill):
  1. snapshot prod org (the rollback)          jrs_inventory.py snapshot --env prod --orgs <Org>
  2. export the folder from the TEST org       (org-scoped login, dependencies + permissions)
  3. export prod's /DataSource/<DS>            (org-scoped login on prod)
  4. build the package                         build_package(test_zip, prod_ds_zip, org, folder)
  5. verify                                    verify_package(): no test host, DS bytes == prod's
  6. import into prod as user|Org              --i-mean-prod
  7. snapshot prod again, diff test:Org vs prod:Org on the folder, run-sweep the folder

    python3 scripts/jaspersoft/jrs_promote_test_to_prod.py --org Fond_Du_Lac \\
        --folder /SmartCity/Report/Standard_Offering --ds FondDuLac_DS [--dry-run] [--i-mean-prod]
--dry-run stops after step 5 and leaves the package under backups/jaspersoft/promotion/.
"""
from __future__ import annotations

import argparse
import io
import os
import pathlib
import re
import sys
import time
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]


def build_package(test_zip: bytes, prod_ds_zip: bytes, org: str, folder: str, ds: str) -> bytes:
    """The test export with its DataSource tree replaced by prod's own, in the server's org-export
    shape (rootTenantId, keyalias/encrypted from prod's export so the datasource password decrypts)."""
    src = zipfile.ZipFile(io.BytesIO(test_zip)); dsz = zipfile.ZipFile(io.BytesIO(prod_ds_zip))
    ds_idx = dsz.read("index.xml").decode()
    keyalias = re.search(r'name="keyalias" value="([^"]+)"', ds_idx).group(1)
    enc = re.search(r'name="encrypted" value="([^"]+)"', ds_idx).group(1)
    jsv = re.search(r'name="jsVersion" value="([^"]+)"', ds_idx).group(1)
    ds_files = {n: dsz.read(n) for n in dsz.namelist() if n.startswith("resources/DataSource/") and not n.endswith("/")}
    if f"resources/DataSource/{ds}.xml" not in ds_files:
        raise SystemExit(f"prod datasource export does not contain resources/DataSource/{ds}.xml: {sorted(ds_files)}")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in ds_files.items():
            z.writestr(n, b)
        for n in src.namelist():
            if n == "index.xml" or n.endswith("/") or n.startswith("resources/DataSource/") or n.startswith("favorites/"):
                continue
            z.writestr(n, src.read(n))
        index = (f'<?xml version="1.0" encoding="UTF-8"?>\n<export><property name="keyalias" value="{keyalias}"/>'
                 f'<module id="repositoryResources"><resource>/DataSource/{ds}</resource><folder>{folder}</folder></module>'
                 f'<module id="favorites"/><property name="pathProcessorId" value="zip"/><property name="rootTenantId" value="{org}"/>'
                 f'<property name="jsVersion" value="{jsv}"/><property name="encrypted" value="{enc}"/></export>')
        z.writestr("index.xml", index.encode())
    return out.getvalue()


def verify_package(pkg: bytes, prod_ds_zip: bytes, ds: str, forbidden_hosts: tuple[str, ...]) -> list[str]:
    """Every reason the package must not be imported; empty means go."""
    z = zipfile.ZipFile(io.BytesIO(pkg)); dsz = zipfile.ZipFile(io.BytesIO(prod_ds_zip)); problems = []
    if z.namelist()[-1] != "index.xml":
        problems.append("index.xml is not the last entry")
    if z.read(f"resources/DataSource/{ds}.xml") != dsz.read(f"resources/DataSource/{ds}.xml"):
        problems.append(f"{ds}.xml in the package is not byte-identical to prod's own export")
    for n in z.namelist():
        if n.endswith("/"):
            continue
        b = z.read(n)
        for h in forbidden_hosts:
            if h.encode() in b:
                problems.append(f"{n} mentions the TEST host {h}")
    idx = z.read("index.xml").decode()
    if f"<resource>/DataSource/{ds}</resource>" not in idx or "rootTenantId" not in idx:
        problems.append("index.xml must list the datasource first and carry rootTenantId")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", required=True); ap.add_argument("--folder", default="/SmartCity/Report/Standard_Offering")
    ap.add_argument("--ds", required=True, help="the datasource name shared by both orgs, e.g. FondDuLac_DS")
    ap.add_argument("--test-host", default="smartcity-db-test", help="a string that must not survive into the package")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    import jrs_inventory as inv
    import jrs_run_sweep as sw
    stamp = time.strftime("%Y%m%d-%H%M%S"); out = REPO / "backups/jaspersoft/promotion"; out.mkdir(parents=True, exist_ok=True)
    base = {e: (os.environ.get(f"JRS_{e}_USER") or os.environ.get("JRS_USER", "")).split("|")[0] for e in ("TEST", "PROD")}
    print(f"[1/7] snapshot prod {a.org} (the rollback)")
    if not a.dry_run:
        inv.snapshot("prod", None, [a.org])
    print(f"[2/7] export {a.folder} from TEST {a.org}")
    os.environ["JRS_ENV"] = "test"; os.environ["JRS_TEST_USER"] = f"{base['TEST']}|{a.org}"
    test_zip = inv.export_zip([a.folder]); (out / f"{a.org}_test_{stamp}.zip").write_bytes(test_zip)
    print(f"[3/7] export /DataSource/{a.ds} from PROD {a.org}")
    os.environ["JRS_ENV"] = "prod"; os.environ["JRS_PROD_USER"] = f"{base['PROD']}|{a.org}"
    prod_ds = inv.export_zip([f"/DataSource/{a.ds}"]); (out / f"{a.org}_prod_ds_{stamp}.zip").write_bytes(prod_ds)
    print("[4/7] build the package"); pkg = build_package(test_zip, prod_ds, a.org, a.folder, a.ds)
    pkg_path = out / f"{a.org}_promote_{stamp}.zip"; pkg_path.write_bytes(pkg)
    print("[5/7] verify"); problems = verify_package(pkg, prod_ds, a.ds, (a.test_host,))
    for p in problems:
        print("   FAIL:", p)
    if problems:
        return 1
    print(f"   PASS: {pkg_path} ({len(pkg)} bytes)")
    if a.dry_run:
        print("dry run: stopping before the import"); return 0
    if not a.i_mean_prod:
        sys.exit("refusing to import into PROD without --i-mean-prod")
    print(f"[6/7] import into PROD {a.org}")
    sw._AUTH.header = sw._auth_for(a.org)
    code, body, _ = sw._http("/rest_v2/import?update=true&skipUserUpdate=true", "POST", pkg, "application/zip")
    import json
    tid = json.loads(body)["id"]
    while True:
        code, body, _ = sw._http(f"/rest_v2/import/{tid}/state"); st = json.loads(body)
        if st.get("phase") in ("finished", "failed"):
            break
        time.sleep(3)
    print("  ", json.dumps(st)[:400])
    if st.get("phase") != "finished" or st.get("warnings"):
        return 1
    print(f"[7/7] snapshot prod {a.org} again; then: jrs_inventory.py diff test:{a.org} prod:{a.org} --folder {a.folder}; jrs_run_sweep.py --env prod --org {a.org} --folder {a.folder} ...")
    inv.snapshot("prod", None, [a.org])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
