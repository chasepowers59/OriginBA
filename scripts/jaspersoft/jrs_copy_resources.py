#!/usr/bin/env python3
"""Copy one Ad Hoc view, or one folder's resources, from one org to another -- across
environments if need be -- touching nothing else in the target.

    python3 scripts/jaspersoft/jrs_copy_resources.py --from prod:CityCorp --to prod:Ellensburg \
        --view /SmartCity/Report/Standard_Offering/Finance/Financial_Transaction/Financial_Transaction___Bill_Cycle_FT_Health
    python3 scripts/jaspersoft/jrs_copy_resources.py --from prod:Fond_Du_Lac --to test:Fond_Du_Lac \
        --folder /SmartCity/Report/FDL_Active_Write_Off_Process [--dry-run] [--i-mean-prod]

Why this is not "export and import". An org-scoped export carries the resource's whole
dependency chain: its domain, its DATASOURCE, shared templates. Imported as-is into another
tenant that overwrites the target's domain and repoints its datasource at the source client's
database. And the package cannot hold the copied resource alone either: the importer resolves
references only against what is inside the package, so a bare package answers "Import
succeeded" with an import.reference.resource.not.found warning and writes nothing (measured on
Ellensburg prod, 2026-09-23).

So the package is the TARGET's own export -- its datasource, its templates, everything outside
the copied scope, byte for byte and verified file by file -- with only the scope's files taken
from the source. A --view scope replaces that view's descriptor and _files; a --folder scope
replaces every file under the folder except the folder's own .folder.xml (its label and
permissions stay the target's).

Checked before anything is written: every domain the scope depends on exposes the same item ids
in both orgs; every field the scope's views reference exists in the target's domains; the
source database host does not survive into the package. Checked after: the target re-exported
matches the source inside the scope and its own prior export outside it (volatile fields
ignored), the datasource connection is unchanged, and every view and report in the scope
executes. The target's prior export is the rollback.
"""
from __future__ import annotations

import argparse
import json
import os
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
# Fields the importer rewrites on every import: version stamps, dates, and the
# <componentType>default</componentType> it adds to input controls (seen on every promotion).
VOLATILE = re.compile(r"<(version|creationDate|updateDate)>[^<]*</\1>|<componentType>default</componentType>")


def parse_target(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise SystemExit(f"--from/--to want env:Org, got {spec!r}")
    env, org = spec.split(":", 1)
    return env, org


def export(env: str, org: str, uri: str, out: pathlib.Path) -> pathlib.Path:
    cmd = [sys.executable, str(HERE / "jrs_repository.py"), "--env", env, "--org", org, "export", uri, "--out", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0 or not out.exists():
        raise SystemExit(f"export {env}:{org}{uri} failed: {r.stdout[-300:]} {r.stderr[-300:]}")
    return out


def files_of(zip_path: pathlib.Path) -> dict[str, bytes]:
    with zipfile.ZipFile(zip_path) as z:
        return {n: z.read(n) for n in z.namelist()}


def in_scope(name: str, scope: str, folder: bool) -> bool:
    """Which package entries the source replaces."""
    if folder:
        prefix = "resources" + scope.rstrip("/") + "/"
        return name.startswith(prefix) and not name.endswith("/.folder.xml")
    leaf = scope.rsplit("/", 1)[-1]
    return f"/{leaf}.xml" in name or f"/{leaf}_files/" in name


def domain_items(files: dict[str, bytes]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for name, data in files.items():
        if not name.endswith("_files/schema.data"):
            continue
        sch = data.decode("utf-8", "replace")
        ids = set()
        for g in re.finditer(r'<itemGroup id="([^"]+)"[^>]*>(.*?)</itemGroup>', sch, re.S):
            for i in re.findall(r'<item id="([^"]+)"', g.group(2)):
                ids.add(f"{g.group(1)}.{i}")
        out[name.rsplit("_files/", 1)[0]] = ids
    return out


def view_fields(files: dict[str, bytes], scope: str, folder: bool) -> set[str]:
    fields: set[str] = set()
    for name, data in files.items():
        if not in_scope(name, scope, folder):
            continue
        text = data.decode("utf-8", "replace")
        if name.endswith("_files/topicJRXML.data"):
            fields |= set(re.findall(r'<field name="([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)"', text))
        elif name.endswith("_files/stateXML.data"):
            fields |= set(re.findall(r'\b([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)\b', text))
    return fields


def db_host(files: dict[str, bytes]) -> str | None:
    for name, data in files.items():
        if "/DataSource/" in name and name.endswith(".xml"):
            m = re.search(r"<connectionUrl>[^<]*?@([^:/<]+)", data.decode("utf-8", "replace"))
            if m:
                return m.group(1)
    return None


def build_package(src: dict[str, bytes], tgt: dict[str, bytes], scope: str, folder: bool, to_org: str, out: pathlib.Path) -> pathlib.Path:
    keep = {n: d for n, d in tgt.items() if n != "index.xml" and not in_scope(n, scope, folder)}
    replaced = {n: d for n, d in src.items() if in_scope(n, scope, folder)}
    if not replaced:
        raise SystemExit(f"the source export holds nothing under {scope}")
    keep.update(replaced)
    envelope = tgt["index.xml"].decode("utf-8", "replace")
    # The server lists a folder export as <folder>, a resource export as <resource>; the importer
    # takes the tag literally (a folder written as <resource> is "Reference resource not found"
    # and nothing inside it lands -- measured on Fond_Du_Lac test, 2026-09-23). Keep the tags.
    entries = re.findall(r"<(folder|resource)>([^<]+)</\1>", envelope) or [("folder" if folder else "resource", scope)]
    props = dict(re.findall(r'<property name="([^"]+)" value="([^"]*)"', envelope))
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n<export>'
             + f'<property name="keyalias" value="{props.get("keyalias", "")}"/>'
             + '<module id="repositoryResources">' + "".join(f"<{k}>{v}</{k}>" for k, v in entries)
             + '</module><module id="favorites"/><property name="pathProcessorId" value="zip"/>'
             + f'<property name="rootTenantId" value="{to_org}"/>'
             + f'<property name="jsVersion" value="{props.get("jsVersion", "")}"/>'
             + (f'<property name="encrypted" value="{props["encrypted"]}"/>' if props.get("encrypted") else "")
             + "</export>")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in keep.items():
            z.writestr(name, data)
        z.writestr("index.xml", index)
    return out


def verify_package(pkg: pathlib.Path, src: dict[str, bytes], tgt: dict[str, bytes], scope: str, folder: bool, to_org: str) -> None:
    files = files_of(pkg)
    index = files.pop("index.xml").decode()
    outside = [n for n in files if not in_scope(n, scope, folder)]
    wrong = [n for n in outside if tgt.get(n) != files[n]]
    if wrong:
        raise SystemExit(f"not the target's own bytes outside the scope: {wrong[:6]}")
    inside = [n for n in files if in_scope(n, scope, folder)]
    wrong = [n for n in inside if src.get(n) != files[n]]
    if wrong:
        raise SystemExit(f"not the source's bytes inside the scope: {wrong[:6]}")
    if not any("/DataSource/" in n and n.endswith(".xml") for n in outside):
        raise SystemExit("no datasource in the package: domain references would not resolve")
    host = db_host(src)
    if host and host != db_host(tgt) and host.encode() in b"".join(files.values()):
        raise SystemExit(f"the source database host {host} survives inside the package")
    if f'value="{to_org}"' not in index:
        raise SystemExit("index.xml does not carry the target rootTenantId")
    print(f"  package: {len(inside)} files from the source inside {scope}, {len(outside)} carried from the target byte for byte")


def normalised(data: bytes) -> bytes:
    """The importer re-serialises a descriptor: stamps, componentType and the whitespace between
    tags all change, the content does not (test Ellensburg 2026-09-23: 0 lines differed once
    whitespace was collapsed, yet the byte compare flagged it)."""
    text = VOLATILE.sub("", data.decode("utf-8", "replace").replace("\r", ""))
    return re.sub(r">\s+<", "><", text).strip().encode()


def verify_after(after: dict[str, bytes], src: dict[str, bytes], before: dict[str, bytes], scope: str, folder: bool) -> list[str]:
    problems = []
    for n, d in after.items():
        if n == "index.xml":
            continue
        want = src.get(n) if in_scope(n, scope, folder) else before.get(n)
        if want is None:
            problems.append(f"unexpected file after import: {n}")
        elif normalised(want) != normalised(d):
            # a re-imported datasource is re-encrypted: compare its connection, not its ciphertext
            if "/DataSource/" in n and re.sub(rb"<connectionPassword>.*?</connectionPassword>", b"", normalised(want), flags=re.S) == \
                    re.sub(rb"<connectionPassword>.*?</connectionPassword>", b"", normalised(d), flags=re.S):
                continue
            problems.append(f"differs after import: {n}")
    return problems


def scope_resources(files: dict[str, bytes], scope: str, folder: bool) -> tuple[list[str], list[str]]:
    views, reports = [], []
    for n, d in files.items():
        if not in_scope(n, scope, folder) or not n.endswith(".xml") or "_files/" in n:
            continue
        uri = "/" + n[len("resources/"):-4]
        head = d[:600].decode("utf-8", "replace")
        if "<adhocDataView" in head:
            views.append(uri)
        elif "<reportUnit" in head:
            reports.append(uri)
    return sorted(views), sorted(reports)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="src", required=True, metavar="env:Org")
    ap.add_argument("--to", dest="dst", required=True, metavar="env:Org")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--view"); g.add_argument("--folder")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    (senv, sorg), (tenv, torg) = parse_target(a.src), parse_target(a.dst)
    scope, folder = (a.folder, True) if a.folder else (a.view, False)
    if tenv == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("a prod target needs --i-mean-prod")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    work = REPO / "backups" / "jaspersoft" / "copy" / f"{senv}_{sorg}_to_{tenv}_{torg}_{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    src = files_of(export(senv, sorg, scope, work / "source.zip"))
    tgt = files_of(export(tenv, torg, scope, work / "target_before.zip"))
    print(f"1. exported both; {(work / 'target_before.zip').relative_to(REPO)} is the rollback")

    s_items, t_items = domain_items(src), domain_items(tgt)
    for path, ids in s_items.items():
        other = t_items.get(path)
        if other is None:
            raise SystemExit(f"the target has no domain at {path}")
        if ids != other and not in_scope(path + "_files/schema.data", scope, folder):
            raise SystemExit(f"domain {path} differs and is outside the scope: only source={sorted(ids - other)[:5]} only target={sorted(other - ids)[:5]}")
    print(f"2. domains: {len(s_items)} in the chain, item ids compatible")
    missing = sorted(f for f in view_fields(src, scope, folder) if not any(f in ids for ids in s_items.values()))
    if missing:
        raise SystemExit(f"the copied views reference fields no domain in the package exposes: {missing[:10]}")
    print("3. every field the copied views reference resolves")

    pkg = build_package(src, tgt, scope, folder, torg, work / "import.zip")
    verify_package(pkg, src, tgt, scope, folder, torg)
    if a.dry_run:
        print(f"4. dry run: {pkg.relative_to(REPO)} built, nothing imported"); return 0

    cmd = ([sys.executable, str(HERE / "jrs_repository.py"), "--env", tenv, "--org", torg, "--confirm", torg]
           + (["--i-mean-prod"] if tenv == "prod" else []) + ["import", str(pkg)])
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 or "warning" in out.lower():
        print(out[-1200:]); raise SystemExit("4. import did not complete cleanly; the target may be unchanged, check the warnings above")
    print("4. import succeeded, no warnings")

    after = files_of(export(tenv, torg, scope, work / "target_after.zip"))
    problems = verify_after(after, src, tgt, scope, folder)
    print("5. target re-exported:", "matches the source inside the scope and itself outside it" if not problems else problems[:8])

    os.environ["JRS_ENV"] = tenv; sw._AUTH.header = sw._auth_for(torg)
    views, reports = scope_resources(after, scope, folder)
    outcomes = {}
    for v in views:
        outcomes[v] = sw.run_view(v, 240)["outcome"]
    for rp in reports:
        outcomes[rp] = sw.run_report(rp, 240)["outcome"]
    print("6. executed in the target:", {k.rsplit("/", 1)[-1]: v for k, v in outcomes.items()})
    ok = not problems and all(o in ("ok", "empty") for o in outcomes.values())
    print("PASS" if ok else "CHECK: a proof did not hold; target_before.zip restores the target")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
