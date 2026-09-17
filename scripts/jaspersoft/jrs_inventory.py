#!/usr/bin/env python3
"""Snapshot a JasperReports Server into the repo -- the backup every change is rolled back from,
and the inventory the three environments are compared with.

    python3 scripts/jaspersoft/jrs_inventory.py snapshot --env test              # every organization
    python3 scripts/jaspersoft/jrs_inventory.py snapshot --env prod --org Odessa
    python3 scripts/jaspersoft/jrs_inventory.py diff test:Origin_DEV prod:Ellensburg [--folder /SmartCity/Report/Standard_Offering]
    python3 scripts/jaspersoft/jrs_inventory.py summary                          # regenerate jaspersoft/inventory/README.md

What a snapshot is. For each organization the server's OWN export (POST /rest_v2/export with
the org's URI and repository permissions) is downloaded as a zip -- that zip re-imports, so it
is the rollback -- and unpacked into a diffable tree:

    backups/jaspersoft/<env>/<YYYYMMDD-HHMMSS>/<org>.zip        gitignored, the exact server export
    jaspersoft/inventory/<env>/<org>/resources/...              committed: one .xml per resource,
                                                                .data files for JRXML / domain schemas /
                                                                Ad Hoc state, .folder.xml per folder
    jaspersoft/inventory/<env>/<org>.summary.json               counts by type, folders, datasources
    jaspersoft/inventory/README.md                              one table per environment

Committed copies REDACT jdbc <connectionPassword> (it is ciphertext bound to the server key,
but it does not belong in git); the backup zip keeps it, which is what makes the zip a rollback.
Export dates/versions inside the XML are left as exported: `diff` ignores them.

Rules (see .claude/skills/jaspersoft-server-operations): snapshot BEFORE any change, never
change prod or a client org without an explicit instruction naming it, diff AFTER.
"""
from __future__ import annotations

import argparse
import datetime
import io
import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jrs_repository import ENVS, _call, env_name  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "jaspersoft" / "inventory"
BACKUPS = REPO / "backups" / "jaspersoft"
ORG_ROOT = "/organizations/organization_1/organizations"
VOLATILE = re.compile(r"<(creationDate|updateDate|version)>[^<]*</\1>")
PASSWORD = re.compile(r"<connectionPassword>[^<]*</connectionPassword>")


# ------------------------------------------------------------------ server side
def organizations() -> list[str]:
    code, text = _call("/rest_v2/organizations")
    if code != 200:
        sys.exit(f"organizations: {code} {text[:200]}")
    return [o["id"] for o in json.loads(text).get("organization", []) if o["id"] != "organization_1"]


def org_uri(org: str) -> str:
    return f"{ORG_ROOT}/{org}"


def export_zip(uris: list[str]) -> bytes:
    """The server's export of these URIs with repository permissions; polls the task to done."""
    body = json.dumps({"uris": uris, "parameters": ["repository-permissions"]}).encode()
    code, text = _call("/rest_v2/export", method="POST", body=body, ctype="application/json")
    if code not in (200, 201):
        sys.exit(f"export request: {code} {text[:300]}")
    tid = json.loads(text)["id"]
    for _ in range(600):
        code, text = _call(f"/rest_v2/export/{tid}/state")
        st = json.loads(text) if text.startswith("{") else {"phase": text}
        if st.get("phase") == "finished":
            break
        if st.get("phase") == "failed":
            sys.exit(f"export failed: {st}")
        time.sleep(2)
    else:
        sys.exit(f"export {tid} did not finish")
    url_base, auth = __import__("jrs_repository")._cfg()
    import urllib.request
    req = urllib.request.Request(f"{url_base}/rest_v2/export/{tid}/export.zip")
    req.add_header("Authorization", auth)
    with urllib.request.urlopen(req, timeout=1800, context=__import__("jrs_repository")._ssl_context()) as r:
        return r.read()


# ------------------------------------------------------------------ files
def redact(text: str) -> str:
    return PASSWORD.sub("<connectionPassword>REDACTED</connectionPassword>", text)


def unpack(zip_bytes: bytes, dest: Path) -> int:
    """The export tree, committed shape: XML with passwords redacted, .data files verbatim."""
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            out = dest / info.filename
            out.parent.mkdir(parents=True, exist_ok=True)
            data = z.read(info)
            if info.filename.endswith(".xml"):
                out.write_text(redact(data.decode("utf-8", "replace")), encoding="utf-8")
            else:
                out.write_bytes(data)
            n += 1
    return n


def summarize(tree: Path) -> dict:
    """Counts by resource type, the folder tree, and the datasources -- from the export XML."""
    types: dict[str, int] = {}
    folders: list[str] = []
    datasources: list[dict] = []
    reports: list[str] = []
    for f in sorted(tree.rglob("*.xml")):
        if f.name == "index.xml":
            continue
        head = f.read_text(encoding="utf-8", errors="replace")[:400]
        m = re.search(r"<(\w+)[\s>]", head.split("?>", 1)[-1])
        tag = m.group(1) if m else "?"
        rel = f.relative_to(tree / "resources") if (tree / "resources") in f.parents else f
        if tag == "folder":
            folders.append("/" + rel.parent.as_posix().replace("organizations/organization_1/organizations/", "").split("/", 1)[-1] if "/" in rel.parent.as_posix() else "/")
            continue
        if "_files/" in rel.as_posix():
            continue
        types[tag] = types.get(tag, 0) + 1
        uri = "/" + rel.as_posix()[:-4]
        if tag == "jdbcDataSource":
            body = f.read_text(encoding="utf-8", errors="replace")
            url = re.search(r"<connectionUrl>([^<]*)</connectionUrl>", body)
            user = re.search(r"<connectionUser>([^<]*)</connectionUser>", body)
            datasources.append({"uri": uri, "url": url.group(1) if url else None, "user": user.group(1) if user else None})
        if tag == "reportUnit":
            reports.append(uri)
    return {"resources_by_type": dict(sorted(types.items())), "folders": sorted(set(folders)),
            "datasources": datasources, "report_units": reports}


def snapshot(env: str, only_org: str | None) -> None:
    os.environ["JRS_ENV"] = env
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    orgs = [only_org] if only_org else organizations()
    print(f"[{env}] organizations: {orgs}")
    for org in orgs:
        t0 = time.time()
        data = export_zip([org_uri(org)])
        bdir = BACKUPS / env / stamp
        bdir.mkdir(parents=True, exist_ok=True)
        (bdir / f"{org}.zip").write_bytes(data)
        n = unpack(data, INVENTORY / env / org)
        summary = summarize(INVENTORY / env / org)
        summary["snapshot"] = {"env": env, "org": org, "taken": stamp, "backup": str((bdir / f"{org}.zip").relative_to(REPO)), "files": n}
        (INVENTORY / env / f"{org}.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(f"[{env}] {org}: {n} files, {len(data) // 1024} KB, {summary['resources_by_type']} ({time.time() - t0:.0f}s)")
    write_readme()


# ------------------------------------------------------------------ reading back
def write_readme() -> None:
    lines = ["# Jaspersoft inventory", "",
             "Generated by `scripts/jaspersoft/jrs_inventory.py snapshot`; one folder per environment and",
             "organization, the server's own export unpacked (passwords redacted). The re-importable zip of",
             "each snapshot is under `backups/jaspersoft/<env>/<stamp>/` (gitignored). Never hand-edit.", ""]
    for env in ENVS:
        summaries = sorted((INVENTORY / env).glob("*.summary.json")) if (INVENTORY / env).exists() else []
        if not summaries:
            continue
        lines += [f"## {env}", "", "| Organization | Snapshot | Report units | Domains | Ad Hoc views | Dashboards | Input controls | Datasources |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
        for sf in summaries:
            s = json.loads(sf.read_text()); t = s["resources_by_type"]
            ds = ", ".join(f"{d['uri'].rsplit('/', 1)[-1]} ({(d['url'] or '?').split('@')[-1].split('/')[0]})" for d in s["datasources"])
            lines.append(f"| {s['snapshot']['org']} | {s['snapshot']['taken']} | {t.get('reportUnit', 0)} | {t.get('semanticLayerDataSource', 0)} | "
                         f"{t.get('adhocDataView', 0)} | {t.get('dashboard', 0)} | {t.get('inputControl', 0)} | {ds} |")
        lines.append("")
    (INVENTORY / "README.md").write_text("\n".join(lines))


def _normalized_files(tree: Path, folder: str | None) -> dict[str, str]:
    out = {}
    base = tree / "resources"
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(base).as_posix()
        rel_org = re.sub(r"^/organizations/organization_1/organizations/[^/]+", "", rel)
        if folder and not rel_org.startswith(folder):
            continue
        if f.suffix == ".xml":
            body = VOLATILE.sub("", f.read_text(encoding="utf-8", errors="replace"))
            body = re.sub(r"/organizations/organization_1/organizations/[^/<\"]+", "/organizations/organization_1/organizations/ORG", body)
        else:
            body = f.read_bytes().hex()
        out[rel_org] = body
    return out


def diff(a: str, b: str, folder: str | None) -> int:
    (ea, oa), (eb, ob) = a.split(":", 1), b.split(":", 1)
    fa, fb = _normalized_files(INVENTORY / ea / oa, folder), _normalized_files(INVENTORY / eb / ob, folder)
    only_a, only_b = sorted(set(fa) - set(fb)), sorted(set(fb) - set(fa))
    changed = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    print(f"{a} vs {b}" + (f" under {folder}" if folder else ""))
    for label, items in (("only in " + a, only_a), ("only in " + b, only_b), ("different", changed)):
        print(f"  {label}: {len(items)}")
        for k in items[:40]:
            print(f"    {k}")
        if len(items) > 40:
            print(f"    ... {len(items) - 40} more")
    return 0 if not (only_a or only_b or changed) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("--env", choices=ENVS, required=True); s.add_argument("--org")
    d = sub.add_parser("diff"); d.add_argument("a", help="env:Org"); d.add_argument("b", help="env:Org"); d.add_argument("--folder")
    sub.add_parser("summary")
    a = ap.parse_args()
    if a.cmd == "snapshot":
        snapshot(a.env, a.org); return 0
    if a.cmd == "diff":
        return diff(a.a, a.b, a.folder)
    write_readme(); return 0


if __name__ == "__main__":
    sys.exit(main())
