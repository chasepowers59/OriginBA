#!/usr/bin/env python3
"""Snapshot a JasperReports Server into the repo -- the backup every change is rolled back from,
and the inventory the three environments are compared with.

    python3 scripts/jaspersoft/jrs_inventory.py snapshot --env test              # every organization
    python3 scripts/jaspersoft/jrs_inventory.py snapshot --env prod --org Odessa
    python3 scripts/jaspersoft/jrs_inventory.py diff test:Origin_DEV prod:Ellensburg [--folder /SmartCity/Report/Standard_Offering]
    python3 scripts/jaspersoft/jrs_inventory.py summary                          # regenerate jaspersoft/inventory/README.md
    python3 scripts/jaspersoft/jrs_inventory.py clients                          # jaspersoft/inventory/CLIENTS.md: what each org contains
    python3 scripts/jaspersoft/jrs_inventory.py rebuild --env test               # re-unpack the latest backup zips after a policy change

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


# Not committed: the Ad Hoc view's generated topicJRXML (37.8 MB of the 64 MB an org exports --
# derived from the domain + stateXML, which IS committed) and rendered outputs. The backup zip
# keeps everything; the committed tree is what a person or a diff needs to read.
NOT_COMMITTED = ("topicJRXML.data",)
NOT_COMMITTED_SUFFIXES = (".pdf", ".xlsx", ".docx", ".pptx")


def unpack(zip_bytes: bytes, dest: Path) -> int:
    """The export tree, committed shape: XML with passwords redacted, .data files verbatim,
    minus NOT_COMMITTED."""
    if dest.exists():
        shutil.rmtree(dest)
    n = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename.rsplit("/", 1)[-1]
            if name in NOT_COMMITTED or name.lower().endswith(NOT_COMMITTED_SUFFIXES):
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
        if tag.endswith("DataSource") and tag != "semanticLayerDataSource":
            body = f.read_text(encoding="utf-8", errors="replace")
            url = re.search(r"<connectionUrl>([^<]*)</connectionUrl>", body)
            user = re.search(r"<connectionUser>([^<]*)</connectionUser>", body)
            jndi = re.search(r"<jndiName>([^<]*)</jndiName>", body)
            datasources.append({"uri": uri, "kind": tag, "url": url.group(1) if url else None,
                                "user": user.group(1) if user else None, "jndi": jndi.group(1) if jndi else None})
        if tag == "reportUnit":
            reports.append(uri)
    return {"resources_by_type": dict(sorted(types.items())), "folders": sorted(set(folders)),
            "datasources": datasources, "report_units": reports}


def snapshot(env: str, only_org: str | None, orgs_scoped: list[str] | None = None) -> None:
    """A superuser exports each org by its /organizations/... URI. An ORG-SCOPED account (prod:
    the login is user|Org, it sees only that org) exports its own root, "/", once per org with
    the login re-scoped -- pass --orgs A B C for that shape."""
    os.environ["JRS_ENV"] = env
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_user = os.environ.get(f"JRS_{env.upper()}_USER") or os.environ.get("JRS_USER", "")
    base_user = base_user.split("|")[0]
    scoped = orgs_scoped is not None
    orgs = orgs_scoped or ([only_org] if only_org else organizations())
    print(f"[{env}] organizations: {orgs}" + (" (org-scoped logins)" if scoped else ""))
    for org in orgs:
        t0 = time.time()
        if scoped:
            os.environ[f"JRS_{env.upper()}_USER"] = f"{base_user}|{org}"
        data = export_zip(["/"] if scoped else [org_uri(org)])
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
        lines += [f"## {env}", "", "| Organization | Snapshot | Report units | Domains | Ad Hoc views | Dashboards | Files | Datasources (user @ host) |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
        for sf in summaries:
            s = json.loads(sf.read_text()); t = s["resources_by_type"]
            ds = ", ".join(f"{d['uri'].rsplit('/', 1)[-1]} ({d.get('user') or '?'} @ {(d.get('url') or d.get('jndi') or '?').split('@')[-1].split('/')[0]})" for d in s["datasources"])
            lines.append(f"| {s['snapshot']['org']} | {s['snapshot']['taken']} | {t.get('reportUnit', 0)} | {t.get('semanticLayerDataSource', 0)} | "
                         f"{t.get('adhocDataView', 0)} | {t.get('dashboardModelResource', 0)} | {t.get('fileResource', 0)} | {ds} |")
        lines.append("")
    (INVENTORY / "README.md").write_text("\n".join(lines))


# ------------------------------------------------------------------ what each client contains
def _tree_counts(tree: Path) -> dict[str, dict[str, int]]:
    """Resources by TYPE under each folder path (org-relative), the folder's own contents only."""
    base = tree / "resources"
    out: dict[str, dict[str, int]] = {}
    for f in sorted(base.rglob("*.xml")):
        if f.name in ("index.xml", ".folder.xml") or "_files/" in f.as_posix():
            continue
        rel = re.sub(r"^organizations/organization_1/organizations/[^/]+", "", f.relative_to(base).as_posix())
        folder = "/" + rel.rsplit("/", 1)[0].strip("/") if "/" in rel else "/"
        head = f.read_text(encoding="utf-8", errors="replace")[:300].split("?>", 1)[-1]
        m = re.search(r"<(\w+)[\s>]", head); tag = m.group(1) if m else "?"
        out.setdefault(folder, {})[tag] = out.setdefault(folder, {}).get(tag, 0) + 1
    return out


SHORT = {"reportUnit": "reports", "semanticLayerDataSource": "domains", "adhocDataView": "views",
         "dashboardModelResource": "dashboards", "inputControl": "controls", "fileResource": "files",
         "jdbcDataSource": "datasources", "contentResource": "outputs"}


def _rollup(counts: dict[str, dict[str, int]], prefix: str, depth: int) -> list[tuple[str, dict[str, int]]]:
    """Folders directly under prefix (depth levels), each with everything beneath it summed."""
    rows: dict[str, dict[str, int]] = {}
    for folder, c in counts.items():
        if not (folder == prefix or folder.startswith(prefix.rstrip("/") + "/")):
            continue
        rest = folder[len(prefix.rstrip("/")):].strip("/")
        key = "/".join(rest.split("/")[:depth]) if rest else "."
        agg = rows.setdefault(key, {})
        for t, n in c.items():
            agg[t] = agg.get(t, 0) + n
    return sorted(rows.items())


def write_clients() -> None:
    lines = ["# What each organization contains", "",
             "Generated from the inventory (`jrs_inventory.py clients`). Counts are resources under the",
             "folder, all depths: reports = report units, domains = semantic layers, views = Ad Hoc views.",
             "Datasources show user @ host/service. Never hand-edit; re-run after a snapshot.", ""]
    for env in ENVS:
        if not (INVENTORY / env).exists():
            continue
        for sf in sorted((INVENTORY / env).glob("*.summary.json")):
            s = json.loads(sf.read_text()); org = s["snapshot"]["org"]
            counts = _tree_counts(INVENTORY / env / org)
            total: dict[str, int] = {}
            for c in counts.values():
                for t, n in c.items():
                    total[t] = total.get(t, 0) + n
            lines += [f"## {env} / {org}", "",
                      "Snapshot " + s["snapshot"]["taken"] + " · " + ", ".join(f"{n} {SHORT.get(t, t)}" for t, n in sorted(total.items(), key=lambda x: -x[1])), ""]
            if s["datasources"]:
                lines += ["| Datasource | User | Connection |", "| --- | --- | --- |"]
                for d in s["datasources"]:
                    lines.append(f"| {d['uri'].rsplit('/', 1)[-1]} | {d.get('user') or ''} | {(d.get('url') or d.get('jndi') or '')} |")
                lines.append("")
            top = _rollup(counts, "/", 1)
            lines += ["| Top-level folder | Contents |", "| --- | --- |"]
            for key, c in top:
                lines.append(f"| /{key if key != '.' else ''} | " + ", ".join(f"{n} {SHORT.get(t, t)}" for t, n in sorted(c.items(), key=lambda x: -x[1])) + " |")
            lines.append("")
            for section in ("/SmartCity/Report/Standard_Offering", "/SmartCity/Report/Workstreams", "/SmartCity/Letter", "/SmartCity/Bill"):
                rows = _rollup(counts, section, 1)
                if not rows:
                    continue
                lines += [f"**{section}**", "", "| Folder | Contents |", "| --- | --- |"]
                for key, c in rows:
                    lines.append(f"| {key} | " + ", ".join(f"{n} {SHORT.get(t, t)}" for t, n in sorted(c.items(), key=lambda x: -x[1])) + " |")
                lines.append("")
    (INVENTORY / "CLIENTS.md").write_text("\n".join(lines))


# ------------------------------------------------------------------ environments compared
def _resource_index(tree: Path) -> dict[str, tuple[str, str]]:
    """org-relative uri -> (type, content hash of the descriptor + its files, volatile fields dropped)."""
    import hashlib
    base = tree / "resources"
    out = {}
    files = _normalized_files(tree, None)
    for rel, body in files.items():
        if rel.endswith("/.folder.xml") or "_files/" in rel or not rel.endswith(".xml"):
            continue
        uri = rel[:-4]
        m = re.search(r"<(\w+)[\s>]", body.split("?>", 1)[-1]); tag = m.group(1) if m else "?"
        h = hashlib.sha1(body.encode()).hexdigest()[:10]
        deps = sorted(k for k in files if k.startswith(uri + "_files/"))
        if deps:
            h = hashlib.sha1((h + "".join(files[k] if isinstance(files[k], str) else "" for k in deps)).encode()).hexdigest()[:10]
        out[uri] = (tag, h)
    return out


def write_environments() -> None:
    envs = {e: sorted(p.stem.replace(".summary", "") for p in (INVENTORY / e).glob("*.summary.json")) for e in ENVS if (INVENTORY / e).exists()}
    lines = ["# The three environments, compared", "",
             "Generated by `jrs_inventory.py environments` from the committed inventory. A resource is",
             "'same' when its descriptor and files match with dates, versions and the organization path",
             "ignored; 'differs' when the content differs; counts exclude folders and generated topicJRXML.", "",
             "| Environment | Server | Organizations |", "| --- | --- | --- |"]
    versions = {"test": "JRS 10.0.0 PRO (build 20260514_1415)", "prod": "JRS 9.0.0 PRO (build 20260514_1241) -- 10.0 upgrade planned", "internal": "JRS 10.0.0 PRO"}
    for e, orgs in envs.items():
        lines.append(f"| {e} | {versions.get(e, '?')} | {', '.join(orgs)} |")
    lines.append("")
    pairs = [("test", "prod"), ("internal", "test")]
    for ea, eb in pairs:
        common = sorted(set(envs.get(ea, [])) & set(envs.get(eb, [])))
        if not common:
            continue
        lines += [f"## {ea} vs {eb}", ""]
        for org in common:
            ia, ib = _resource_index(INVENTORY / ea / org), _resource_index(INVENTORY / eb / org)
            only_a = sorted(set(ia) - set(ib)); only_b = sorted(set(ib) - set(ia))
            same = sorted(k for k in set(ia) & set(ib) if ia[k][1] == ib[k][1])
            diff = sorted(k for k in set(ia) & set(ib) if ia[k][1] != ib[k][1])
            lines += [f"### {org}", "",
                      f"{len(same)} same · {len(diff)} differ · {len(only_a)} only in {ea} · {len(only_b)} only in {eb}", ""]
            def bucket(items, idx):
                by: dict[str, list] = {}
                for k in items:
                    by.setdefault(SHORT.get(idx[k][0], idx[k][0]), []).append(k)
                return by
            for label, items, idx in ((f"only in {ea}", only_a, ia), (f"only in {eb}", only_b, ib), ("differ", diff, ia)):
                if not items:
                    continue
                by = bucket(items, idx)
                lines.append(f"**{label}** — " + ", ".join(f"{len(v)} {t}" for t, v in sorted(by.items(), key=lambda x: -len(x[1]))))
                lines.append("")
                for t, v in sorted(by.items(), key=lambda x: -len(x[1])):
                    for k in v[:15]:
                        lines.append(f"- {t}: `{k}`")
                    if len(v) > 15:
                        lines.append(f"- {t}: … {len(v) - 15} more")
                lines.append("")
    (INVENTORY / "ENVIRONMENTS.md").write_text("\n".join(lines))


# server-owned trees that differ by server, never by anyone's work: skipped in comparisons
NOT_COMPARED = ("/themes/", "/temp/", "/adhoc/", "/public/")


def _normalized_files(tree: Path, folder: str | None) -> dict[str, str]:
    """org-relative path -> comparable content. A superuser export carries
    /organizations/organization_1/organizations/<Org> in paths AND inside descriptors; an
    org-scoped export (prod) carries neither. Both are reduced to the org-relative form."""
    out = {}
    base = tree / "resources"
    org_prefix = re.compile(r"/organizations/organization_1/organizations/[^/<\"]+")
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        rel = "/" + f.relative_to(base).as_posix()
        rel_org = org_prefix.sub("", rel) or "/"
        if folder and not rel_org.startswith(folder):
            continue
        if any(rel_org.startswith(n) for n in NOT_COMPARED):
            continue
        if f.suffix == ".xml":
            body = VOLATILE.sub("", f.read_text(encoding="utf-8", errors="replace"))
            body = org_prefix.sub("", body)
            # JRS 10 exports carry <permission> blocks, JRS 9 does not; permissions are compared
            # separately if ever needed, never as "content differs"
            body = re.sub(r"<permission>.*?</permission>", "", body, flags=re.S)
            body = re.sub(r"\s+", " ", body)          # export pretty-printing differs by server version
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
    s.add_argument("--orgs", nargs="+", help="org-scoped login shape: snapshot each of these orgs as user|Org")
    d = sub.add_parser("diff"); d.add_argument("a", help="env:Org"); d.add_argument("b", help="env:Org"); d.add_argument("--folder")
    sub.add_parser("summary")
    sub.add_parser("clients", help="write jaspersoft/inventory/CLIENTS.md: what each organization contains")
    sub.add_parser("environments", help="write jaspersoft/inventory/ENVIRONMENTS.md: test vs prod, internal vs test, per org")
    r = sub.add_parser("rebuild", help="re-unpack the latest backup zips (after a policy change), no server needed")
    r.add_argument("--env", choices=ENVS, required=True)
    a = ap.parse_args()
    if a.cmd == "snapshot":
        snapshot(a.env, a.org, a.orgs); return 0
    if a.cmd == "diff":
        return diff(a.a, a.b, a.folder)
    if a.cmd == "rebuild":
        rebuild(a.env); return 0
    if a.cmd == "clients":
        write_clients(); return 0
    if a.cmd == "environments":
        write_environments(); return 0
    write_readme(); return 0


def rebuild(env: str) -> None:
    stamps = sorted(d for d in (BACKUPS / env).iterdir() if d.is_dir()) if (BACKUPS / env).exists() else []
    if not stamps:
        sys.exit(f"no backups under {BACKUPS / env}")
    latest = stamps[-1]
    for z in sorted(latest.glob("*.zip")):
        org = z.stem
        n = unpack(z.read_bytes(), INVENTORY / env / org)
        summary = summarize(INVENTORY / env / org)
        summary["snapshot"] = {"env": env, "org": org, "taken": latest.name, "backup": str(z.relative_to(REPO)), "files": n}
        (INVENTORY / env / f"{org}.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(f"[{env}] {org}: rebuilt from {z.name}, {n} files")
    write_readme()


if __name__ == "__main__":
    sys.exit(main())
