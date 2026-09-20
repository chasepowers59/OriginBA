#!/usr/bin/env python3
"""See what is actually on a JasperReports Server, and import with the answer in hand.

Three servers, one tool: --env test|prod|internal (or JRS_ENV) selects JRS_<ENV>_URL /
JRS_<ENV>_USER / JRS_<ENV>_PASSWORD / JRS_<ENV>_INSECURE from the environment; the test
server also answers to the original JRS_URL / JRS_USER / JRS_PASSWORD keys. Only key names
are ever printed. In a multi-tenant server the user is org-scoped: JRS_USER='jasperadmin|Origin_DEV'
imports INTO Origin_DEV; a bare 'jasperadmin' is organization_1's admin and 'superuser' is
the server root -- a tenant-relative package lands wherever the login is scoped, which is
how an import "succeeds" and nothing appears where you are looking.

    python3 scripts/jaspersoft/jrs_repository.py whoami
    python3 scripts/jaspersoft/jrs_repository.py search billing_by_cycle_period
    python3 scripts/jaspersoft/jrs_repository.py list /SmartCity/Report/Standard_Offering/Finance
    python3 scripts/jaspersoft/jrs_repository.py import deploy/finance_pack_jrs_import_Origin_DEV_DS.zip [--no-update]

Everything else a deployment needs, in the same tool (every write needs --confirm <Org>, the org
the login is scoped to, named back; on prod also --i-mean-prod; --dry-run prints the call):
    --org Origin_DEV copy   /SmartCity/Report/X /SmartCity/Report/Archive   --confirm Origin_DEV
    --org Origin_DEV move   /SmartCity/Report/X /SmartCity/Report/Y         --confirm Origin_DEV
    --org Origin_DEV delete /SmartCity/Report/X/old_report                  --confirm Origin_DEV
    --org Origin_DEV mkdir  /SmartCity/Report/New_Folder --label "New Folder" --confirm Origin_DEV
    --org Origin_DEV perms  /SmartCity/Report/Standard_Offering
    --org Origin_DEV perms-set /SmartCity/Report/X role/ROLE_BILLING:18 role/ROLE_ADMINISTRATOR:1 --confirm Origin_DEV
    --org Origin_DEV jobs [--report /SmartCity/Report/X/r] | job ID | job-run ID | job-delete ID
    --org Origin_DEV users [--role ROLE_BILLING] | roles
    --org Origin_DEV export /SmartCity/Report/Standard_Offering/Finance --out backups/finance.zip
    --org Origin_DEV run /SmartCity/Report/Standard_Offering/Finance/gl_by_distribution_code_period --format pdf --param FROM_DT=2026-08-01 --param TO_DT=2026-08-31
Copy and move name the destination FOLDER; the server keeps the resource's own name.
Rule of the estate: snapshot the org before any write (jrs_inventory.py snapshot), diff after.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import ssl
import urllib.request


def _ssl_context() -> ssl.SSLContext | None:
    """The SmartCity TEST server presents a self-signed chain. JRS_CA_BUNDLE points at its
    certificate (preferred); JRS_INSECURE=true skips verification for a test server only."""
    bundle = _env_var("CA_BUNDLE")
    if bundle:
        return ssl.create_default_context(cafile=bundle)
    if _env_var("INSECURE").lower() in ("1", "true", "yes"):
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return None


ENVS = ("test", "prod", "internal")


def env_name() -> str:
    return os.environ.get("JRS_ENV", "test").lower()


def _env_var(key: str, env: str | None = None) -> str:
    """JRS_<ENV>_<KEY>, falling back to JRS_<KEY> (the test server's original keys)."""
    e = (env or env_name()).upper()
    return os.environ.get(f"JRS_{e}_{key}") or (os.environ.get(f"JRS_{key}", "") if e == "TEST" else "")


def _cfg() -> tuple[str, str]:
    url, user, pw = _env_var("URL"), _env_var("USER"), _env_var("PASSWORD")
    if not (url and user and pw):
        e = env_name().upper()
        sys.exit(f"set JRS_{e}_URL, JRS_{e}_USER (user|Organization or a superuser) and JRS_{e}_PASSWORD "
                 f"(JRS_ENV or --env selects test|prod|internal)")
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return url.rstrip("/"), f"Basic {token}"


def _call(path: str, *, method: str = "GET", body: bytes | None = None, ctype: str | None = None,
          accept: str = "application/json") -> tuple[int, str]:
    url, auth = _cfg()
    req = urllib.request.Request(url + path, data=body, method=method)
    req.add_header("Authorization", auth)
    req.add_header("Accept", accept)
    if ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=120, context=_ssl_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


# ---- every write goes through here: the org must be named back, prod must be meant, and the
# call is printed before it is made so a --dry-run shows exactly what would hit the server.
WRITES = {"copy", "move", "delete", "mkdir", "perms-set", "job-delete", "job-run", "import"}


def guard_write(cmd: str, a) -> None:
    org = (_env_var("USER").split("|") + [""])[1]
    if env_name() == "prod" and not a.i_mean_prod:
        sys.exit(f"{cmd} on PROD refused: pass --i-mean-prod (and snapshot the org first: jrs_inventory.py snapshot --env prod --orgs {org or '<Org>'})")
    if a.confirm != (org or "ROOT"):
        sys.exit(f"{cmd} refused: the login is scoped to {org or 'the ROOT (no org)'}; pass --confirm {org or 'ROOT'} to say that is the org you mean"
                 + ("" if org else " -- a root-scoped write lands outside every client tenant"))


def _write(method: str, path: str, a, body: bytes | None = None, ctype: str | None = None, headers: dict | None = None) -> tuple[int, str]:
    print(f"{method} {path}" + (f"  headers={headers}" if headers else "") + (f"  body={len(body)}B" if body else ""))
    if a.dry_run:
        return 0, "(dry run)"
    url, auth = _cfg()
    req = urllib.request.Request(url + path, data=body, method=method)
    req.add_header("Authorization", auth); req.add_header("Accept", "application/json")
    if ctype:
        req.add_header("Content-Type", ctype)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=300, context=_ssl_context()) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def _show(code: int, text: str) -> int:
    print(code, text[:800] if text else "")
    return 0 if code in (0, 200, 201, 204) else 1


def copy_or_move(cmd: str, src: str, dst: str, a) -> int:
    """POST copies, PUT moves: Content-Location names the source, the URL names the DESTINATION
    FOLDER (the server keeps the resource's own name). createFolders makes the target path."""
    return _show(*_write("POST" if cmd == "copy" else "PUT", f"/rest_v2/resources{urllib.parse.quote(dst)}?createFolders=true&overwrite={'true' if a.overwrite else 'false'}", a,
                         headers={"Content-Location": src}))


def delete(uri: str, a) -> int:
    return _show(*_write("DELETE", f"/rest_v2/resources{urllib.parse.quote(uri)}", a))


def mkdir(uri: str, label: str | None, a) -> int:
    body = json.dumps({"label": label or uri.rsplit("/", 1)[-1].replace("_", " ")}).encode()
    return _show(*_write("PUT", f"/rest_v2/resources{urllib.parse.quote(uri)}?createFolders=true", a, body, "application/repository.folder+json"))


def perms(uri: str) -> int:
    code, text = _call(f"/rest_v2/permissions{urllib.parse.quote(uri)}?effectivePermissions=false")
    if code != 200:
        return _show(code, text)
    for p in json.loads(text).get("permission", []):
        print(f"  {p.get('mask'):>3}  {p.get('recipient')}")
    print("masks: 0 none, 1 administer, 2 read, 4 write, 8 delete, 32 execute (18 = read+execute, 30 = read+write+delete+execute)")
    return 0


def perms_set(uri: str, grants: list[str], a) -> int:
    """role/ROLE_X:mask or user/name:mask, e.g. role/ROLE_BILLING:18 -- the whole list REPLACES the
    resource's own permissions (PUT), so name every recipient you want to keep."""
    perm = []
    for g in grants:
        recipient, mask = g.rsplit(":", 1)
        perm.append({"uri": uri, "recipient": recipient, "mask": int(mask)})
    body = json.dumps({"permission": perm}).encode()
    return _show(*_write("PUT", f"/rest_v2/permissions{urllib.parse.quote(uri)}", a, body, "application/collection+json"))


def jobs(report_uri: str | None) -> int:
    q = f"?reportUnitURI={urllib.parse.quote(report_uri)}" if report_uri else ""
    code, text = _call(f"/rest_v2/jobs{q}")
    if code == 204:
        print("no scheduled jobs" + (f" on {report_uri}" if report_uri else "")); return 0
    if code != 200:
        return _show(code, text)
    for j in json.loads(text).get("jobsummary", []):
        print(f"  job {j.get('id'):>6}  {j.get('label')!r:40}  {j.get('reportUnitURI')}  state={j.get('state', {}).get('value')}  next={j.get('state', {}).get('nextFireTime')}")
    return 0


def job(cmd: str, job_id: str, a) -> int:
    if cmd == "job":
        code, text = _call(f"/rest_v2/jobs/{job_id}", accept="application/job+json"); return _show(code, text)
    if cmd == "job-delete":
        return _show(*_write("DELETE", f"/rest_v2/jobs/{job_id}", a))
    return _show(*_write("POST", f"/rest_v2/jobs/{job_id}/run", a))


def users(role: str | None) -> int:
    code, text = _call("/rest_v2/users" + (f"?requiredRole={urllib.parse.quote(role)}" if role else ""))
    if code != 200:
        return _show(code, text)
    for u in json.loads(text).get("user", []):
        print(f"  {u.get('username'):30} {u.get('fullName', '')!r:32} enabled={u.get('enabled')} ext={u.get('externallyDefined')}")
    return 0


def roles() -> int:
    code, text = _call("/rest_v2/roles")
    if code != 200:
        return _show(code, text)
    print("  " + ", ".join(r.get("name") for r in json.loads(text).get("role", [])))
    return 0


def export(uris: list[str], out: str) -> int:
    """The server's own export of these URIs with dependencies and permissions -- the same call
    jrs_inventory.py's snapshot makes; the zip re-imports as-is (org-scoped login: rootTenantId set)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import jrs_inventory as inv
    data = inv.export_zip(uris)
    open(out, "wb").write(data)
    print(f"wrote {out}: {len(data)} bytes for {uris}")
    return 0


def run(uri: str, fmt: str, params: list[str], out: str | None) -> int:
    q = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in (p.split("=", 1) for p in params))
    url, auth = _cfg()
    req = urllib.request.Request(f"{url}/rest_v2/reports{urllib.parse.quote(uri)}.{fmt}" + (f"?{q}" if q else ""))
    req.add_header("Authorization", auth)
    try:
        with urllib.request.urlopen(req, timeout=600, context=_ssl_context()) as r:
            body = r.read(); code = r.status
    except urllib.error.HTTPError as e:
        body = e.read(); code = e.code
    if code != 200:
        print(code, body[:600].decode("utf-8", "replace")); return 1
    out = out or f"{uri.rsplit('/', 1)[-1]}.{fmt}"
    open(out, "wb").write(body); print(f"200 {len(body)} bytes -> {out}")
    return 0


def whoami() -> int:
    code, text = _call("/rest_v2/users/" + urllib.parse.quote(os.environ["JRS_USER"].split("|")[0])
                       + ("" if "|" not in os.environ["JRS_USER"] else ""), accept="application/json")
    print(code, text[:600])
    code, text = _call("/rest_v2/serverInfo")
    print("serverInfo:", code, text[:400])
    return 0


def search(q: str) -> int:
    code, text = _call(f"/rest_v2/resources?q={urllib.parse.quote(q)}&recursive=true&limit=100")
    print(code)
    if code == 204:
        print("no resources match", q)
        return 1
    try:
        items = json.loads(text).get("resourceLookup", [])
        for it in items:
            print(f"  {it.get('resourceType'):14} {it.get('uri')}")
        print(f"{len(items)} resource(s)")
    except ValueError:
        print(text[:1200])
    return 0


def list_folder(folder: str) -> int:
    code, text = _call(f"/rest_v2/resources?folderUri={urllib.parse.quote(folder)}&recursive=false&limit=200")
    print(code)
    if code == 204:
        print("empty or absent:", folder)
        return 1
    try:
        for it in json.loads(text).get("resourceLookup", []):
            print(f"  {it.get('resourceType'):14} {it.get('uri')}")
    except ValueError:
        print(text[:1200])
    return 0


def do_import(zip_path: str, update: bool) -> int:
    with open(zip_path, "rb") as f:
        body = f.read()
    params = f"update={'true' if update else 'false'}&skipUserUpdate=true"
    code, text = _call(f"/rest_v2/import?{params}", method="POST", body=body, ctype="application/zip")
    print("import request:", code, text[:400])
    if code not in (200, 201):
        return 1
    task = json.loads(text)
    tid = task.get("id")
    for _ in range(120):
        # JRS 10 answers /import/<id> with the task's PARAMETERS (and 404 once it is gone);
        # the phase and the failure reason live under /state (learned 2026-09-18, when an
        # org-scoped import failed import.root.into.organization.not.allowed and the poll
        # loop reported "still running" for two minutes)
        code, text = _call(f"/rest_v2/import/{tid}/state")
        state = json.loads(text) if text.startswith("{") else {"phase": text}
        if state.get("phase") in ("finished", "failed"):
            print(json.dumps(state, indent=2))
            if state.get("warnings"):
                print("WARNINGS -- treat as a failed deploy until each is explained")
            return 0 if state.get("phase") == "finished" and not state.get("warnings") else 1
        time.sleep(1)
    print("import task still running:", tid)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", choices=ENVS, default=None, help="which server: test (default), prod, internal")
    ap.add_argument("--org", help="re-scope the login as user|Org for this call (the org a tenant-relative path belongs to)")
    ap.add_argument("--confirm", metavar="ORG", help="required on every write: the org the login is scoped to, named back")
    ap.add_argument("--i-mean-prod", action="store_true", help="required on every write to prod")
    ap.add_argument("--dry-run", action="store_true", help="print the call a write would make and stop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    s = sub.add_parser("search"); s.add_argument("q")
    l = sub.add_parser("list"); l.add_argument("folder")
    i = sub.add_parser("import"); i.add_argument("zip"); i.add_argument("--no-update", action="store_true")
    for c in ("copy", "move"):
        x = sub.add_parser(c, help=f"{c} a resource into a destination FOLDER"); x.add_argument("src"); x.add_argument("dst"); x.add_argument("--overwrite", action="store_true")
    d = sub.add_parser("delete"); d.add_argument("uri")
    m = sub.add_parser("mkdir"); m.add_argument("uri"); m.add_argument("--label")
    pr = sub.add_parser("perms", help="who can do what on a resource"); pr.add_argument("uri")
    ps = sub.add_parser("perms-set", help="REPLACE a resource's permissions: role/ROLE_X:18 user/name:30 ..."); ps.add_argument("uri"); ps.add_argument("grants", nargs="+")
    j = sub.add_parser("jobs", help="scheduled report jobs, optionally for one report"); j.add_argument("--report")
    for c in ("job", "job-delete", "job-run"):
        x = sub.add_parser(c); x.add_argument("id")
    u = sub.add_parser("users"); u.add_argument("--role")
    sub.add_parser("roles")
    e = sub.add_parser("export", help="the server's export zip of these URIs (dependencies + permissions)"); e.add_argument("uris", nargs="+"); e.add_argument("--out", required=True)
    r = sub.add_parser("run", help="execute a report unit"); r.add_argument("uri"); r.add_argument("--format", default="pdf"); r.add_argument("--param", action="append", default=[]); r.add_argument("--out")
    a = ap.parse_args()
    if a.env:
        os.environ["JRS_ENV"] = a.env
    if a.org:
        e_ = env_name().upper(); base = _env_var("USER").split("|")[0]
        os.environ[f"JRS_{e_}_USER"] = f"{base}|{a.org}"
    if a.cmd in WRITES:
        guard_write(a.cmd, a)
    if a.cmd == "whoami": return whoami()
    if a.cmd == "search": return search(a.q)
    if a.cmd == "list": return list_folder(a.folder)
    if a.cmd == "import": return do_import(a.zip, not a.no_update)
    if a.cmd in ("copy", "move"): return copy_or_move(a.cmd, a.src, a.dst, a)
    if a.cmd == "delete": return delete(a.uri, a)
    if a.cmd == "mkdir": return mkdir(a.uri, a.label, a)
    if a.cmd == "perms": return perms(a.uri)
    if a.cmd == "perms-set": return perms_set(a.uri, a.grants, a)
    if a.cmd == "jobs": return jobs(a.report)
    if a.cmd in ("job", "job-delete", "job-run"): return job(a.cmd, a.id, a)
    if a.cmd == "users": return users(a.role)
    if a.cmd == "roles": return roles()
    if a.cmd == "export": return export(a.uris, a.out)
    return run(a.uri, a.format, a.param, a.out)


if __name__ == "__main__":
    sys.exit(main())
