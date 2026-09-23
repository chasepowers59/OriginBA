#!/usr/bin/env python3
"""Copy ONE Ad Hoc view from a working client org into another, touching nothing else.

Why this is not just "export and import": an org-scoped export of a view carries its whole
dependency chain -- the domain AND the datasource. Imported as-is into another tenant that would
overwrite the target's domain and repoint its datasource at the source client's database.

Nor can the package hold the view alone: the importer resolves a resource's references only
against what is inside the package, so a view-only package "succeeds" with an
import.reference.resource.not.found warning and writes nothing (measured, Ellensburg prod
2026-09-23). So the package is the TARGET's own export -- its datasource and its domain, byte for
byte, verified as such -- with only the view's files taken from the source org.

Precondition, checked and refused if it fails: the two orgs' domains must expose the SAME item
ids, or the copied view references fields the target domain does not have.

    python3 scripts/jaspersoft/jrs_copy_view_between_orgs.py --env prod \
        --from CityCorp --to Ellensburg \
        --view /SmartCity/Report/Standard_Offering/Finance/Financial_Transaction/Financial_Transaction___Bill_Cycle_FT_Health \
        [--dry-run] [--i-mean-prod]

The target's current copy is exported first and is the rollback. After the import the view is
executed and its field references are re-checked against the target domain.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402

REPO = HERE.parents[1]


def export(env: str, org: str, uri: str, out: pathlib.Path) -> pathlib.Path:
    cmd = [sys.executable, str(HERE / "jrs_repository.py"), "--env", env, "--org", org, "export", uri, "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not out.exists():
        raise SystemExit(f"export {org}{uri} failed: {r.stdout[-300:]} {r.stderr[-300:]}")
    return out


def domain_items(zip_path: pathlib.Path) -> dict[str, set[str]]:
    """Every {set}.{item} each domain in the package exposes, keyed by the domain's path."""
    out: dict[str, set[str]] = {}
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            if not name.endswith("_files/schema.data"):
                continue
            sch = z.read(name).decode("utf-8", "replace")
            ids = set()
            for g in re.finditer(r'<itemGroup id="([^"]+)"[^>]*>(.*?)</itemGroup>', sch, re.S):
                for i in re.findall(r'<item id="([^"]+)"', g.group(2)):
                    ids.add(f"{g.group(1)}.{i}")
            out[name.rsplit("_files/", 1)[0]] = ids
    return out


def view_fields(zip_path: pathlib.Path, view: str) -> set[str]:
    leaf = view.rsplit("/", 1)[-1]
    with zipfile.ZipFile(zip_path) as z:
        state = next((z.read(n).decode("utf-8", "replace") for n in z.namelist()
                      if n.endswith(f"{leaf}_files/stateXML.data")), "")
        topic = next((z.read(n).decode("utf-8", "replace") for n in z.namelist()
                      if n.endswith(f"{leaf}_files/topicJRXML.data")), "")
    fields = set(re.findall(r'<field name="([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)"', topic))
    fields |= set(re.findall(r'\b([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)\b', state))
    return fields


def build_package(src_zip: pathlib.Path, tgt_zip: pathlib.Path, view: str, to_org: str, out: pathlib.Path) -> pathlib.Path:
    """The view's own files from the SOURCE, inside the TARGET's export envelope."""
    leaf = view.rsplit("/", 1)[-1]
    # The importer resolves a resource's references ONLY against what is in the package: a package
    # holding the view alone imports "successfully" with an
    # import.reference.resource.not.found warning and silently writes nothing (measured on
    # Ellensburg prod, 2026-09-23). So the package is the TARGET's own export -- its datasource and
    # its domain, byte for byte -- with only the view's files replaced by the source org's.
    keep: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(tgt_zip) as z:
        for n in z.namelist():
            if n == "index.xml":
                continue
            if f"/{leaf}.xml" in n or f"/{leaf}_files/" in n:
                continue                      # the target's own copy of the view: replaced below
            keep.append((n, z.read(n)))
    with zipfile.ZipFile(src_zip) as z:
        view_files = [(n, z.read(n)) for n in z.namelist() if f"/{leaf}.xml" in n or f"/{leaf}_files/" in n]
    if not any(f"/{leaf}.xml" in n for n, _ in view_files):
        raise SystemExit(f"the source export does not contain {leaf}.xml")
    keep += view_files

    with zipfile.ZipFile(tgt_zip) as z:
        envelope = z.read("index.xml").decode("utf-8", "replace")
        tgt_resources = re.findall(r"<resource>([^<]+)</resource>", envelope)
    props = dict(re.findall(r'<property name="([^"]+)" value="([^"]*)"', envelope))
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n<export>'
             + f'<property name="keyalias" value="{props.get("keyalias", "")}"/>'
             + '<module id="repositoryResources">'
             + "".join(f"<resource>{r}</resource>" for r in (tgt_resources or [view]))
             + '</module><module id="favorites"/>'
             + '<property name="pathProcessorId" value="zip"/>'
             + f'<property name="rootTenantId" value="{to_org}"/>'
             + f'<property name="jsVersion" value="{props.get("jsVersion", "")}"/>'
             + (f'<property name="encrypted" value="{props["encrypted"]}"/>' if props.get("encrypted") else "")
             + "</export>")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in keep:
            z.writestr(name, data)
        z.writestr("index.xml", index)
    return out


def verify(pkg: pathlib.Path, tgt_zip: pathlib.Path, view: str, from_org: str, to_org: str) -> None:
    """Everything except the view must be the TARGET's own bytes, or this repoints a client."""
    leaf = view.rsplit("/", 1)[-1]
    with zipfile.ZipFile(pkg) as z:
        names = [n for n in z.namelist() if n != "index.xml"]
        index = z.read("index.xml").decode()
        pkg_files = {n: z.read(n) for n in names}
    with zipfile.ZipFile(tgt_zip) as z:
        tgt_files = {n: z.read(n) for n in z.namelist() if n != "index.xml"}

    carried = [n for n in pkg_files if f"/{leaf}.xml" not in n and f"/{leaf}_files/" not in n]
    changed = [n for n in carried if tgt_files.get(n) != pkg_files[n]]
    if changed:
        raise SystemExit(f"these are not the target's own bytes: {changed[:6]}")
    ds = [n for n in carried if "/DataSource/" in n and n.endswith(".xml")]
    if not ds:
        raise SystemExit("no datasource in the package: the domain reference will not resolve")
    if from_org.encode() in b"".join(pkg_files.values()):
        raise SystemExit(f"the source org name {from_org} survives inside the package")
    if f'value="{to_org}"' not in index:
        raise SystemExit("index.xml does not carry the TARGET rootTenantId")
    if f"<resource>{view}</resource>" not in index:
        raise SystemExit("index.xml does not list the view")
    # The server's own export lists ONLY the requested resource and ships its dependencies as
    # files; the importer reads them from the package to resolve references. Keep that shape.
    print(f"  verified: {len(names)} entries; {len(carried)} carried from the target byte for byte "
          f"(datasource {[pathlib.PurePosixPath(d).name for d in ds]}), only the view replaced")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True)
    ap.add_argument("--from", dest="src", required=True); ap.add_argument("--to", dest="dst", required=True)
    ap.add_argument("--view", required=True)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    if a.env == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("prod needs --i-mean-prod")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    work = REPO / "backups" / "jaspersoft" / "view_copy" / f"{a.env}_{a.src}_to_{a.dst}_{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    src_zip = export(a.env, a.src, a.view, work / f"{a.src}.zip")
    tgt_zip = export(a.env, a.dst, a.view, work / f"{a.dst}_before.zip")
    print(f"1. exported both copies; {tgt_zip.relative_to(REPO)} is the rollback")

    src_items = domain_items(src_zip); tgt_items = domain_items(tgt_zip)
    for path, ids in src_items.items():
        other = tgt_items.get(path)
        if other is None:
            raise SystemExit(f"the target has no domain at {path}: copy the domain first")
        if ids != other:
            only_src, only_tgt = sorted(ids - other)[:6], sorted(other - ids)[:6]
            raise SystemExit(f"domains differ at {path}: only in {a.src}={only_src}, only in {a.dst}={only_tgt}")
    print(f"2. domains match item for item ({sum(len(v) for v in src_items.values())} items)")

    missing = sorted(f for f in view_fields(src_zip, a.view)
                     if not any(f in ids for ids in tgt_items.values()))
    if missing:
        raise SystemExit(f"the view references fields the target domain lacks: {missing[:10]}")
    print("3. every field the view references exists in the target domain")

    pkg = build_package(src_zip, tgt_zip, a.view, a.dst, work / f"{a.dst}_import.zip")
    verify(pkg, tgt_zip, a.view, a.src, a.dst)
    if a.dry_run:
        print(f"4. dry run: {pkg.relative_to(REPO)} built, nothing imported"); return 0

    # jrs_repository.py takes its guards as GLOBAL flags, before the subcommand; appending them
    # after `import <zip>` is an argparse error, not a write.
    cmd = ([sys.executable, str(HERE / "jrs_repository.py"), "--env", a.env, "--org", a.dst, "--confirm", a.dst]
           + (["--i-mean-prod"] if a.env == "prod" else [])
           + ["import", str(pkg)])
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print("4. import:", (r.stdout or r.stderr).strip()[-300:])
    if r.returncode != 0:
        raise SystemExit("import failed; the target is unchanged")

    sw._AUTH.header = None
    import os
    os.environ["JRS_ENV"] = a.env; sw._AUTH.header = sw._auth_for(a.dst)
    res = sw.run_view(a.view, 240)
    print("5. executed in the target:", json.dumps(res))
    return 0 if res["outcome"] in ("ok", "empty") else 1


if __name__ == "__main__":
    sys.exit(main())
