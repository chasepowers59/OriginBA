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
        code, text = _call(f"/rest_v2/import/{tid}")
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
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    s = sub.add_parser("search"); s.add_argument("q")
    l = sub.add_parser("list"); l.add_argument("folder")
    i = sub.add_parser("import"); i.add_argument("zip"); i.add_argument("--no-update", action="store_true")
    a = ap.parse_args()
    if a.env:
        os.environ["JRS_ENV"] = a.env
    if a.cmd == "whoami":
        return whoami()
    if a.cmd == "search":
        return search(a.q)
    if a.cmd == "list":
        return list_folder(a.folder)
    return do_import(a.zip, not a.no_update)


if __name__ == "__main__":
    sys.exit(main())
