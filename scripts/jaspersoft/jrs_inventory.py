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
import urllib.error
import urllib.parse
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


class ExportStuck(Exception):
    pass


def export_zip(uris: list[str], cap_seconds: int = 1800, attempts: int = 3) -> bytes:
    """The server's export of these URIs with repository permissions; polls the task to done.
    Raises ExportStuck past cap_seconds -- prod's 9.0 exporter never finishes some folders
    (Fond_Du_Lac 2026-09-18), and a snapshot must not hang on one of them. A download cut
    mid-stream (VPN; College_Station prod, twice) is retried as a WHOLE new export: the server
    discards a finished export once its download starts, so a Range retry answers 404."""
    for attempt in range(1, attempts + 1):
        tid = _export_task(uris, cap_seconds)
        try:
            return _download(f"/rest_v2/export/{tid}/export.zip")
        except DownloadCut as exc:
            print(f"{exc}; re-exporting {uris} ({attempt}/{attempts})")
    raise ExportStuck(f"download of {uris} cut {attempts} times")


def _export_task(uris: list[str], cap_seconds: int) -> str:
    body = json.dumps({"uris": uris, "parameters": ["repository-permissions"]}).encode()
    code, text = _call("/rest_v2/export", method="POST", body=body, ctype="application/json")
    if code not in (200, 201):
        raise ExportStuck(f"export request: {code} {text[:300]}")
    tid = json.loads(text)["id"]
    t0 = time.time()
    while time.time() - t0 < cap_seconds:
        try:
            code, text = _call(f"/rest_v2/export/{tid}/state")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            # a transient TLS EOF on one poll (College_Station prod, 2026-09-18) must not
            # end a 40-minute snapshot; the export keeps running server-side
            print(f"state poll failed ({type(exc).__name__}); retrying")
            time.sleep(5); continue
        st = json.loads(text) if text.startswith("{") else {"phase": text}
        if st.get("phase") == "finished":
            return tid
        if st.get("phase") == "failed":
            raise ExportStuck(f"export failed: {st}")
        time.sleep(2)
    raise ExportStuck(f"export of {uris} still running after {cap_seconds}s")


class DownloadCut(Exception):
    pass


def _download(path: str) -> bytes:
    import http.client
    import urllib.error
    import urllib.request
    url_base, auth = __import__("jrs_repository")._cfg()
    req = urllib.request.Request(url_base + path)
    req.add_header("Authorization", auth)
    held = bytearray()
    try:
        with urllib.request.urlopen(req, timeout=600, context=__import__("jrs_repository")._ssl_context()) as r:
            while chunk := r.read(1 << 20):
                held += chunk
        return bytes(held)
    except (http.client.IncompleteRead, ConnectionError, TimeoutError, urllib.error.URLError) as exc:
        raise DownloadCut(f"download cut after {len(held) // 1024} KB ({type(exc).__name__})") from exc


# ------------------------------------------------------------------ files
def redact(text: str) -> str:
    return PASSWORD.sub("<connectionPassword>REDACTED</connectionPassword>", text)


# Not committed: the Ad Hoc view's generated topicJRXML (37.8 MB of the 64 MB an org exports --
# derived from the domain + stateXML, which IS committed) and rendered outputs. The backup zip
# keeps everything; the committed tree is what a person or a diff needs to read.
NOT_COMMITTED = ("topicJRXML.data",)
NOT_COMMITTED_SUFFIXES = (".pdf", ".xlsx", ".docx", ".pptx")


def unpack(zip_bytes: bytes, dest: Path, fresh: bool = True) -> int:
    """The export tree, committed shape: XML with passwords redacted, .data files verbatim,
    minus NOT_COMMITTED. fresh=False adds a part to an existing tree."""
    if fresh and dest.exists():
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


def _export_part(uri: str, cap: int, tries: int = 3) -> bytes | None:
    """One part's zip, or None when the server never finishes it. A dropped connection
    (RemoteDisconnected on the POST, TLS EOF on a poll) is retried as a fresh export."""
    import http.client
    for attempt in range(1, tries + 1):
        try:
            return export_zip([uri], cap_seconds=cap)
        except ExportStuck as exc:
            print(f"  {uri}: {exc}")
            return None
        except (urllib.error.URLError, http.client.HTTPException, ConnectionError, TimeoutError) as exc:
            print(f"  {uri}: connection dropped ({type(exc).__name__}); retry {attempt}/{tries}")
            time.sleep(10)
    return None


def _part_uris(parts: list[str], exclude: tuple[str, ...] = ()) -> list[str]:
    """Top-level folders of the login's root, with the folders named in `parts` replaced by
    their children (so a slow branch is exported one child at a time); `exclude` are URIs
    known to hang the exporter, left out without waiting for the cap."""
    code, text = _call("/rest_v2/resources?folderUri=/&recursive=false&limit=200")
    tops = [i["uri"] for i in json.loads(text).get("resourceLookup", []) if i["resourceType"] == "folder"] if code == 200 else []
    out: list[str] = []
    for u in tops:
        out += _expand(u, parts)
    return [u for u in out if u not in exclude]


def _expand(uri: str, parts: list[str]) -> list[str]:
    if uri not in parts:
        return [uri]
    code, text = _call(f"/rest_v2/resources?folderUri={urllib.parse.quote(uri)}&recursive=false&limit=500")
    kids = json.loads(text).get("resourceLookup", []) if code == 200 else []
    out = [i["uri"] for i in kids if i["resourceType"] != "folder"]
    for i in kids:
        if i["resourceType"] == "folder":
            out += _expand(i["uri"], parts)
    return out


def snapshot(env: str, only_org: str | None, orgs_scoped: list[str] | None = None,
             parts: list[str] | None = None, part_cap: int = 600, exclude: tuple[str, ...] = (),
             resume: bool = False) -> None:
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
        if resume and parts:
            # continue the newest stamp: parts whose zip already landed are not asked for again
            # (the network to prod drops a connection every 10-15 minutes, 2026-09-18)
            stamps = sorted(d for d in (BACKUPS / env).glob("*") if any(d.glob(f"{org}__*.zip")))
            if stamps:
                stamp = stamps[-1].name
        bdir = BACKUPS / env / stamp
        bdir.mkdir(parents=True, exist_ok=True)
        stuck = list(exclude)
        if parts:
            # one export per folder (recursing into --split folders), each under its own cap;
            # a folder the server never finishes is recorded, not waited for
            tree = INVENTORY / env / org
            if tree.exists() and not resume:
                shutil.rmtree(tree)
            n, size = 0, 0
            for uri in _part_uris(parts, exclude):
                zpath = bdir / f"{org}__{uri.strip('/').replace('/', '__') or 'root'}.zip"
                if resume and zpath.exists():
                    part = zpath.read_bytes()
                else:
                    part = _export_part(uri, part_cap)
                    if part is None:
                        print(f"[{env}] {org}: SKIPPED {uri}")
                        stuck.append(uri); continue
                    zpath.write_bytes(part)
                n += unpack(part, tree, fresh=False); size += len(part)
            data = b""
        else:
            data = export_zip(["/"] if scoped else [org_uri(org)])
            (bdir / f"{org}.zip").write_bytes(data)
            n, size = unpack(data, INVENTORY / env / org), len(data)
        summary = summarize(INVENTORY / env / org)
        summary["snapshot"] = {"env": env, "org": org, "taken": stamp, "backup": str((bdir).relative_to(REPO)) + ("/" + org + "__*.zip" if parts else f"/{org}.zip"),
                               "files": n, "parts": bool(parts), "stuck": stuck}
        (INVENTORY / env / f"{org}.summary.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(f"[{env}] {org}: {n} files, {size // 1024} KB, {summary['resources_by_type']} ({time.time() - t0:.0f}s)" + (f"; stuck: {stuck}" if stuck else ""))
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
        partial = []
        for sf in summaries:
            s = json.loads(sf.read_text()); t = s["resources_by_type"]
            if s["snapshot"].get("stuck"):
                partial.append(s)
            ds = ", ".join(f"{d['uri'].rsplit('/', 1)[-1]} ({d.get('user') or '?'} @ {(d.get('url') or d.get('jndi') or '?').split('@')[-1].split('/')[0]})" for d in s["datasources"])
            lines.append(f"| {s['snapshot']['org']} | {s['snapshot']['taken']} | {t.get('reportUnit', 0)} | {t.get('semanticLayerDataSource', 0)} | "
                         f"{t.get('adhocDataView', 0)} | {t.get('dashboardModelResource', 0)} | {t.get('fileResource', 0)} | {ds} |")
        for s in partial:
            lines.append(f"\nPartial: {s['snapshot']['org']} is missing {', '.join('`' + u + '`' for u in s['snapshot']['stuck'])} "
                         "(the server's exporter never finishes them; see the operations skill).")
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
    s.add_argument("--split", nargs="*", metavar="FOLDER", help="export folder by folder instead of the root; the named folders are split into their children")
    s.add_argument("--part-cap", type=int, default=600, help="seconds to wait for one part before recording it as stuck")
    s.add_argument("--exclude", nargs="*", default=[], metavar="URI", help="parts known to hang the exporter; recorded as stuck, never requested")
    s.add_argument("--resume", action="store_true", help="with --split: keep the newest backup's parts and the tree, export only the missing parts")
    d = sub.add_parser("diff"); d.add_argument("a", help="env:Org"); d.add_argument("b", help="env:Org"); d.add_argument("--folder")
    sub.add_parser("summary")
    sub.add_parser("clients", help="write jaspersoft/inventory/CLIENTS.md: what each organization contains")
    sub.add_parser("environments", help="write jaspersoft/inventory/ENVIRONMENTS.md: test vs prod, internal vs test, per org")
    r = sub.add_parser("rebuild", help="re-unpack the latest backup zips (after a policy change), no server needed")
    r.add_argument("--env", choices=ENVS, required=True)
    a = ap.parse_args()
    if a.cmd == "snapshot":
        snapshot(a.env, a.org, a.orgs, a.split if a.split is not None else None, a.part_cap, tuple(a.exclude), a.resume); return 0
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
