#!/usr/bin/env python3
"""Promote resources -- domains, report units, Ad Hoc views, dashboards, whole folders -- from one
org to another as the superuser, across servers if need be, touching nothing else in the target.

    scripts/jaspersoft/jrs.sh jrs_promote.py --from test:Origin_DEV --to test:Odessa \\
        --resource /SmartCity/Report/Standard_Offering/Finance/Adjustments/Adjustment_AP_Request___Domain \\
        --resource /SmartCity/Report/Standard_Offering/Finance/adj_ap_requests_control \\
        --into /SmartCity/Report/Standard_Offering/Finance/Adjustments --ds Origin_DataVergence_DS \\
        [--param FROM_DT=2025-01-01 --param TO_DT=2026-09-30] [--replace] [--dry-run] [--i-mean-prod]

Root on every server (test, prod, internal) exports and imports with ABSOLUTE paths
(/organizations/organization_1/organizations/<Org>/...), so no per-org login is needed: an org
whose users are not ours (Odessa) is reached exactly like any other, and a prod org the same way
as test. --into is the destination folder (default: the source path); --ds the target's
datasource when the org has more than one.

The package is BUILT, never imported as exported. The scope's files come from the source with
every path rewritten onto the target org and the destination folder, and every datasource
reference (descriptor uri, alias, schema datasourceId) repointed at the target's own datasource.
Everything the scope references outside itself -- that datasource, a view's domain -- travels as
the TARGET's own export of it, byte for byte, listed first, because the importer resolves
references only against the package (measured 2026-09-23) and must not be handed the source's.
Nothing else of the source export travels. Resources land without explicit permissions, so they
inherit the destination folder's.

Before the import: the destination folder exists on the target or is created in the package;
every outside reference exists on the target at the rewritten path, and a referenced domain
exposes every field the copied views use; the source org's path, datasource name and database
host survive nowhere in the package; a destination already occupied is refused without
--replace, and exported first as the rollback. After: the target's export of everything in the
package matches it (importer stamps ignored; a datasource compared on its connection, not its
re-encrypted password), and every promoted domain / report / view / dashboard executes.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_inventory as inv  # noqa: E402
import jrs_run_sweep as sw  # noqa: E402
from jrs_copy_resources import db_host, domain_items, normalised  # noqa: E402

REPO = HERE.parents[1]
ORGS = "/organizations/organization_1/organizations/"
# a resource uri ends where its descriptor, its _files folder, a child path or a tag begins
BOUNDARY = r'(?=/|\.xml|_files|["<]|$)'


def org_root(org: str) -> str:
    return ORGS + org


# ------------------------------------------------------------------ pure: package building
def scope_names(files: dict[str, bytes], src_org: str, uris: list[str]) -> set[str]:
    out: set[str] = set()
    for uri in uris:
        base = f"resources{org_root(src_org)}{uri}"
        out |= {n for n in files if n == base + ".xml" or n.startswith(base + "_files/") or n.startswith(base + "/")}
    return out


def moves(src_org: str, tgt_org: str, uris: list[str], into: str | None, src_ds: str, tgt_ds: str) -> list[tuple[str, str]]:
    """Ordered path substitutions: each resource onto its destination, the datasource onto the
    target's, then the org root for every other reference; longest first so a resource's own
    move wins over the org-wide one."""
    src, tgt = org_root(src_org), org_root(tgt_org)
    mv = [(src + u, tgt + (f"{into.rstrip('/')}/{u.rsplit('/', 1)[-1]}" if into else u)) for u in uris]
    if src_ds:
        mv.append((f"{src}/DataSource/{src_ds}", f"{tgt}/DataSource/{tgt_ds}"))
    mv.append((src, tgt))
    return sorted(mv, key=lambda m: -len(m[0]))


def rewrite(text: str, mv: list[tuple[str, str]], src_ds: str, tgt_ds: str) -> str:
    for old, new in mv:
        text = re.sub(re.escape(old) + BOUNDARY, lambda _m, new=new: new, text)
    if src_ds and src_ds != tgt_ds:
        # descriptor alias, and the two places a domain schema names its datasource
        for old, new in ((f"<alias>{src_ds}</alias>", f"<alias>{tgt_ds}</alias>"), (f'datasourceId="{src_ds}"', f'datasourceId="{tgt_ds}"'),
                         (f'DataSource id="{src_ds}"', f'DataSource id="{tgt_ds}"')):
            text = text.replace(old, new)
    return text


def _text(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:   # an image inside a dashboard's _files: carried as is
        return None


def datasources_in(files: dict[str, bytes], names) -> set[str]:
    out: set[str] = set()
    for n in names:
        m = re.match(r"resources.*/DataSource/([^/]+)\.xml$", n)
        if m:
            if m.group(1) != ".folder":
                out.add(m.group(1))
            continue
        text = _text(files[n]) or ""
        out |= set(re.findall(r"/DataSource/([^/<]+)</uri>", text)) | set(re.findall(r'datasourceId="([^"]+)"', text))
    return out


def resource_uri(path: str) -> str:
    """The resource a package entry (without the `resources` prefix) belongs to."""
    if path.endswith("/.folder.xml"):
        return path[: -len("/.folder.xml")]
    if "_files/" in path:
        return path.split("_files/", 1)[0]
    return path[:-4] if path.endswith(".xml") else path


def rewritten_scope(src: dict[str, bytes], scope: set[str], mv, src_ds: str, tgt_ds: str) -> dict[str, bytes]:
    """The scope's files under their new names with their contents rewritten. A promoted
    resource's own descriptor (or a folder's .folder.xml) names its PARENT, which no path move
    covers when the destination is a different folder: that one element is repointed first."""
    dest = dict(mv)
    out = {}
    for n in sorted(scope):
        path = n[len("resources"):]
        text = _text(src[n])
        if text is not None:
            own = resource_uri(path)
            if own in dest and (path == own + ".xml" or path == own + "/.folder.xml"):
                tag = "folder" if path.endswith(".xml") and not path.endswith("/.folder.xml") else "parent"
                text = text.replace(f"<{tag}>{own.rsplit('/', 1)[0]}</{tag}>", f"<{tag}>{dest[own].rsplit('/', 1)[0]}</{tag}>", 1)
            text = rewrite(text, mv, src_ds, tgt_ds)
        out["resources" + rewrite(path, mv, "", "")] = text.encode() if text is not None else src[n]
    return out


def external_references(src: dict[str, bytes], scope: set[str], mv, src_ds: str, tgt_ds: str, tgt_org: str) -> set[str]:
    """Every <uri> the rewritten scope points at that the scope itself does not provide."""
    files = rewritten_scope(src, scope, mv, src_ds, tgt_ds)
    inside = {resource_uri(n[len("resources"):]) for n in files}
    ds = f"{org_root(tgt_org)}/DataSource/{tgt_ds}" if tgt_ds else None
    refs: set[str] = set()
    for d in files.values():
        refs |= set(re.findall(r"<uri>([^<]+)</uri>", _text(d) or ""))
    return {u for u in refs if u not in inside and u != ds}


def unresolved_fields(src: dict[str, bytes], scope: set[str], items: set[str]) -> set[str]:
    fields: set[str] = set()
    for n in scope:
        text = _text(src[n]) or ""
        if n.endswith("_files/topicJRXML.data"):
            fields |= set(re.findall(r'<field name="([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)"', text))
        elif n.endswith("_files/stateXML.data"):
            fields |= set(re.findall(r"\b([A-Z][A-Z0-9_]*\.[A-Z][A-Z0-9_]*)\b", text))
    return fields - items


def folder_xml(tgt_org: str, uri: str) -> bytes:
    parent, name = uri.rsplit("/", 1)
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<folder exportedWithPermissions="false">\n    <parent>{org_root(tgt_org)}{parent}</parent>\n'
            f'    <name>{name}</name>\n    <label>{name.replace("_", " ")}</label>\n    <creationDate>{now}</creationDate>\n    <updateDate>{now}</updateDate>\n</folder>\n').encode()


def build_package(src: dict[str, bytes], scope: set[str], tgt_files: dict[str, bytes], mv, src_ds: str, tgt_ds: str,
                  new_folders: list[str], new_uris: list[str], tgt_org: str) -> bytes:
    """tgt_files: the target's own exports (datasource + anything the scope references), carried
    byte for byte; new_folders: destination folders the target lacks, shallowest first;
    new_uris: where each promoted resource lands (tenant-relative)."""
    tgt = org_root(tgt_org)
    props = dict(re.findall(r'<property name="([^"]+)" value="([^"]*)"', tgt_files["index.xml"].decode("utf-8", "replace")))
    # a root export drags every ancestor .folder.xml along, up to /organizations itself; only the
    # referenced resources travel, never a folder the target already has
    carried = {n: d for n, d in tgt_files.items() if n != "index.xml" and not n.endswith("/.folder.xml") and not n.endswith("/")}
    files = rewritten_scope(src, scope, mv, src_ds, tgt_ds)
    entries = [("resource", f"{tgt}/DataSource/{tgt_ds}")] if tgt_ds else []
    entries += [("resource", "/" + resource_uri(n[len("resources/"):]))
                for n in carried if n.endswith(".xml") and "_files/" not in n and ("resource", "/" + resource_uri(n[len("resources/"):])) not in entries]
    entries += [("folder", tgt + f) for f in new_folders]
    entries += [("folder" if f"resources{tgt}{u}/.folder.xml" in files else "resource", tgt + u) for u in new_uris]
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n<export>'
             + f'<property name="keyalias" value="{props.get("keyalias", "")}"/><module id="repositoryResources">'
             + "".join(f"<{k}>{v}</{k}>" for k, v in entries)
             + '</module><module id="favorites"/><property name="pathProcessorId" value="zip"/>'
             + f'<property name="rootTenantId" value="{props.get("rootTenantId", "organizations")}"/>'
             + f'<property name="jsVersion" value="{props.get("jsVersion", "")}"/>'
             + (f'<property name="encrypted" value="{props["encrypted"]}"/>' if props.get("encrypted") else "") + "</export>")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in carried.items():
            z.writestr(n, d)
        for f in new_folders:
            z.writestr(f"resources{tgt}{f}/.folder.xml", folder_xml(tgt_org, f))
        for n, d in files.items():
            z.writestr(n, d)
        z.writestr("index.xml", index)
    return out.getvalue()


def verify_package(pkg: bytes, tgt_files: dict[str, bytes], src_org: str, src_ds: str, src_host: str | None, tgt_ds: str) -> list[str]:
    files = files_of_bytes(pkg)
    problems = []
    found = sorted(datasources_in(files, [n for n in files if "/DataSource/" in n]))
    if tgt_ds and tgt_ds not in found:
        problems.append(f"no datasource {tgt_ds} in the package (found: {found})")
    for n, d in files.items():
        if "/DataSource/" in n and tgt_files.get(n) != d:
            problems.append(f"datasource file is not the target's own bytes: {n}")
    blob = b"".join(files[n] for n in sorted(files) if n != "index.xml")
    if org_root(src_org).encode() in blob or any(org_root(src_org) in n for n in files):
        problems.append(f"the source org path {org_root(src_org)} survives inside the package")
    if src_host and src_host.encode() in blob:
        problems.append(f"the source database host {src_host} survives inside the package")
    if src_ds and src_ds != tgt_ds and src_ds.encode() in blob:
        problems.append(f"the source datasource name {src_ds} survives inside the package")
    return problems


def files_of_bytes(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return {n: z.read(n) for n in z.namelist()}


def after_problems(after: dict[str, bytes], expected: dict[str, bytes]) -> list[str]:
    problems = []
    for n, want in expected.items():
        got = after.get(n)
        if got is None:
            problems.append(f"missing after import: {n}")
        elif normalised(want) != normalised(got):
            if "/DataSource/" in n and _connection(want) == _connection(got):
                continue   # re-encrypted password, same connection
            problems.append(f"differs after import: {n}")
    return problems


def _connection(data: bytes) -> bytes:
    return re.sub(rb"<connectionPassword>.*?</connectionPassword>", b"", normalised(data), flags=re.S)


# ------------------------------------------------------------------ live: root on either server
def _root(env: str) -> None:
    os.environ["JRS_ENV"] = env
    sw._AUTH.header = None   # the bare login: ROLE_SUPERUSER, absolute paths


def export_root(env: str, uris: list[str], out: pathlib.Path) -> dict[str, bytes]:
    _root(env)
    data = inv.export_zip(uris, permissions=False)
    out.write_bytes(data)
    return files_of_bytes(data)


def exists(uri: str) -> bool:
    code, _, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}", timeout=60)
    return code == 200


def listing(folder: str, recursive: bool) -> list[dict]:
    q = f"folderUri={urllib.parse.quote(folder)}&recursive={'true' if recursive else 'false'}&limit=1000"
    code, body, _ = sw._http(f"/rest_v2/resources?{q}", timeout=120)
    return json.loads(body).get("resourceLookup", []) if code == 200 else []


def probe_domain(uri: str) -> str:
    code, body, _ = sw._http(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=180)
    if code != 200:
        raise RuntimeError(f"metadata {code}: {sw._message(body)[:200]}")
    levels = json.loads(body)["rootLevel"]["subLevels"]
    probe = [f"{l['id']}.{i['id']}" for l in levels for i in l.get("items", [])[:2] if i.get("kind") != "measure"][:12]
    payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": {"select": {"fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(probe)]}}}).encode()
    code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=5", "POST", payload,
                              "application/execution.multiLevelQuery+json", "application/flatData+json", 300)
    if code != 200:
        raise RuntimeError(f"probe query {code}: {sw._message(body)[:200]}")
    return f"{len(levels)} sets, probe of {len(probe)} items answers {json.loads(body).get('totalCounts')} rows in {dt:.1f}s"


def run_report(uri: str, params: list[str], out_dir: pathlib.Path) -> str:
    if params:
        q = urllib.parse.urlencode([tuple(p.split("=", 1)) for p in params])
        code, body, dt = sw._http(f"/rest_v2/reports{urllib.parse.quote(uri)}.pdf?{q}", accept="application/pdf", timeout=600)
        if code != 200 or body[:4] != b"%PDF":
            raise RuntimeError(f"{code}: {sw._message(body)[:200]}")
        pdf = out_dir / (uri.rsplit("/", 1)[-1] + ".pdf"); pdf.write_bytes(body)
        return f"PDF {len(body) // 1024} KB in {dt:.1f}s -> {pdf.relative_to(REPO)}"
    r = sw.run_report(uri, 600)
    if r["outcome"] != "ok":
        raise RuntimeError(r.get("detail", r["outcome"]))
    return f"HTML {r['bytes'] // 1024} KB in {r['seconds']:.1f}s (no --param given)"


def execute(uri: str, kind: str, params: list[str], out_dir: pathlib.Path) -> str:
    if kind == "semanticLayerDataSource":
        return probe_domain(uri)
    if kind == "reportUnit":
        return run_report(uri, params, out_dir)
    if kind in ("adhocDataView", "dashboard"):
        r = (sw.run_view if kind == "adhocDataView" else sw.run_dashboard)(uri, 600)
        if r["outcome"] not in ("ok", "empty"):
            raise RuntimeError(r.get("detail", r["outcome"]))
        return f"{r['outcome']}: {r.get('rows', r.get('bytes'))} in {r['seconds']:.1f}s"
    return f"{kind}: nothing to execute"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--from", dest="src", required=True, metavar="env:Org"); ap.add_argument("--to", dest="dst", required=True, metavar="env:Org")
    ap.add_argument("--resource", action="append", required=True, metavar="URI", help="tenant-relative uri of a resource or folder in the source org (repeatable)")
    ap.add_argument("--into", metavar="FOLDER", help="destination folder in the target org (default: the source's own path)")
    ap.add_argument("--ds", help="the target's datasource name when the org has more than one")
    ap.add_argument("--param", action="append", default=[], metavar="NAME=VALUE", help="passed to every promoted report unit's run")
    ap.add_argument("--replace", action="store_true", help="allow overwriting a resource already at the destination")
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    ap.add_argument("--check-only", action="store_true", help="write nothing: only execute what a previous promotion put at the destination")
    a = ap.parse_args()
    (senv, sorg), (tenv, torg) = (x.split(":", 1) for x in (a.src, a.dst))
    if tenv == "prod" and not a.i_mean_prod and not (a.dry_run or a.check_only):
        raise SystemExit("a prod target needs --i-mean-prod")
    src_root, tgt_root = org_root(sorg), org_root(torg)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    work = REPO / "backups" / "jaspersoft" / "promote" / f"{senv}_{sorg}_to_{tenv}_{torg}_{stamp}"
    work.mkdir(parents=True, exist_ok=True)
    new_uris = [f"{a.into.rstrip('/')}/{u.rsplit('/', 1)[-1]}" if a.into else u for u in a.resource]
    if a.check_only:
        return execute_all(tenv, tgt_root, new_uris, a.param, work, f"{tenv}:{torg} check of {new_uris}")

    src = export_root(senv, [src_root + u for u in a.resource], work / "source.zip")
    scope = scope_names(src, sorg, a.resource)
    if not scope:
        raise SystemExit(f"the source export holds nothing for {a.resource}")
    src_ds_names = datasources_in(src, scope)
    if len(src_ds_names) > 1:
        raise SystemExit(f"the scope uses more than one datasource: {sorted(src_ds_names)}; promote them separately")
    src_ds = next(iter(src_ds_names), "")
    print(f"1. source {senv}:{sorg}: {len(scope)} files in scope" + (f", on datasource {src_ds}" if src_ds else ", no datasource of their own"))

    _root(tenv)
    tgt_ds = a.ds or ""
    if src_ds and not tgt_ds:
        cands = [r["uri"].rsplit("/", 1)[-1] for r in listing(f"{tgt_root}/DataSource", False) if r.get("resourceType") == "jdbcDataSource"]
        if len(cands) != 1:
            raise SystemExit(f"{torg} has {len(cands)} datasources {cands}: pass --ds")
        tgt_ds = cands[0]
    if tgt_ds and not exists(f"{tgt_root}/DataSource/{tgt_ds}"):
        raise SystemExit(f"{torg} has no datasource /DataSource/{tgt_ds}")
    mv = moves(sorg, torg, a.resource, a.into, src_ds, tgt_ds)

    parents = sorted({u.rsplit("/", 1)[0] for u in new_uris}, key=len)
    new_folders: list[str] = []
    for p in parents:
        chain = [p[: m.start()] for m in re.finditer("/", p + "/") if m.start() > 0]
        new_folders += [f for f in chain if f not in new_folders and not exists(tgt_root + f)]
    occupied = [u for u in new_uris if exists(tgt_root + u)]
    if occupied and not a.replace:
        raise SystemExit(f"already at the destination in {torg}: {occupied} (pass --replace to overwrite; nothing was written)")
    if occupied:
        export_root(tenv, [tgt_root + u for u in occupied], work / "target_before.zip")
    print(f"2. target {tenv}:{torg}: datasource {tgt_ds or '-'}; folders to create {new_folders or 'none'}; "
          + (f"replacing {occupied}, rollback {(work / 'target_before.zip').relative_to(REPO)}" if occupied else "destinations free"))

    refs = external_references(src, scope, mv, src_ds, tgt_ds, torg)
    missing = [u for u in refs if not exists(u)]
    if missing:
        raise SystemExit(f"the scope references resources the target lacks: {missing}")
    carry = ([f"{tgt_root}/DataSource/{tgt_ds}"] if tgt_ds else []) + sorted(u for u in refs if u.startswith(tgt_root))
    tgt_files = export_root(tenv, carry, work / "target_carried.zip") if carry else {"index.xml": b""}
    items = set().union(*domain_items(tgt_files).values()) if tgt_files else set()
    bad = unresolved_fields(src, scope, items) if any(n.endswith(("stateXML.data", "topicJRXML.data")) for n in scope) else set()
    if bad:
        raise SystemExit(f"the copied views use fields the target's domains do not expose: {sorted(bad)[:10]}")
    print(f"3. references outside the scope: {len(refs)} all present on the target; carried as the target's own: {[c[len(tgt_root):] for c in carry]}")

    pkg = build_package(src, scope, tgt_files, mv, src_ds, tgt_ds, new_folders, new_uris, torg)
    (work / "import.zip").write_bytes(pkg)
    problems = verify_package(pkg, tgt_files, sorg, src_ds, db_host(src), tgt_ds)
    if problems:
        raise SystemExit("4. package refused: " + "; ".join(problems))
    print(f"4. package {(work / 'import.zip').relative_to(REPO)} ({len(pkg):,} bytes) verified: target bytes outside the scope, no trace of {sorg}")
    if a.dry_run:
        print("5. dry run: nothing imported"); return 0

    _root(tenv)
    code, body, _ = sw._http("/rest_v2/import?update=true&skipUserUpdate=true", "POST", pkg, "application/zip", timeout=600)
    if code not in (200, 201):
        raise SystemExit(f"5. import request: {code} {sw._message(body)[:300]}")
    tid = json.loads(body)["id"]
    while True:
        code, body, _ = sw._http(f"/rest_v2/import/{tid}/state", timeout=120); st = json.loads(body)
        if st.get("phase") in ("finished", "failed"):
            break
        time.sleep(2)
    if st.get("phase") != "finished" or st.get("warnings"):
        raise SystemExit(f"5. import did not complete cleanly: {json.dumps(st)[:800]}")
    print("5. import finished, no warnings")

    expected = {n: d for n, d in files_of_bytes(pkg).items() if n != "index.xml"}
    after = export_root(tenv, carry + [tgt_root + u for u in new_uris] + [tgt_root + f for f in new_folders], work / "target_after.zip")
    problems = after_problems(after, expected)
    if problems:
        raise SystemExit("6. target re-exported: " + "; ".join(problems[:8]))
    print(f"6. target re-exported: all {len(expected)} package files match, datasource connection unchanged")

    return execute_all(tenv, tgt_root, new_uris, a.param, work, f"{tenv}:{torg} <- {senv}:{sorg} {new_uris}")


def execute_all(tenv: str, tgt_root: str, uris: list[str], params: list[str], work: pathlib.Path, what: str) -> int:
    """Step 7: everything at the destination uris (a folder's whole content) executes as root."""
    _root(tenv)
    todo: list[tuple[str, str]] = []
    for u in uris:
        for r in listing((tgt_root + u).rsplit("/", 1)[0], False):
            if r["uri"] == tgt_root + u:
                todo += [(x["uri"], x["resourceType"]) for x in listing(r["uri"], True)] if r["resourceType"] == "folder" else [(r["uri"], r["resourceType"])]
    missing = [u for u in uris if tgt_root + u not in {t[0] for t in todo} and not any(t[0].startswith(tgt_root + u + "/") for t in todo)]
    failed = len(missing)
    for u in missing:
        print(f"   {'':24} {u}: FAILED not on the target")
    for uri, kind in todo:
        try:
            print(f"   {kind:24} {uri[len(tgt_root):]}: {execute(uri, kind, params, work)}")
        except RuntimeError as exc:
            failed += 1; print(f"   {kind:24} {uri[len(tgt_root):]}: FAILED {exc}")
    print(f"7. executed {len(todo)} promoted resources, {failed} failed")
    print(("PASS" if not failed else "FAIL") + f"  {what}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
