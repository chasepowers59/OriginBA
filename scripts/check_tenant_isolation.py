#!/usr/bin/env python3
"""Prove client separation through the running API: real users, real warehouses, HTTP only.

The unit tests prove each guard in isolation (tests/test_admin_org_isolation.py and
friends). This proves the assembled application: it starts its own API with sign-in ON,
a throwaway user database and a throwaway saved-view store, creates the root admin, an
Ellensburg user, an Ellensburg editor and a Demo 25 user, and then tries to cross every
boundary a client user could reach for. Nothing touches the portal's real user database,
its JSON stores in data/analytics_portal/, or any client's CISADM (queries read each
org's reporting warehouse only). The generated passwords are never printed.

    python3 scripts/check_tenant_isolation.py        # Ellensburg needs the VPN

Exit 0 when every boundary held.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("ISOLATION_CHECK_PORT", "8012"))
API = f"http://127.0.0.1:{PORT}"
STATE_DB = "originba_isolation_check"   # on the disposable Docker Postgres (5433)
STATE_URL = f"postgresql://originba:originba@localhost:5433/{STATE_DB}?sslmode=disable"
HOME, OTHER = "ellensburg", "demo25"
PROBE = ("rpt_customer_account", {"dimensions": [], "measures": [{"field": "*", "agg": "count"}],
                                   "filters": [], "all_dates": True, "limit": 5})
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    RESULTS.append((ok, label))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}", flush=True)


def call(method: str, path: str, token: str | None = None, body: dict | None = None,
         org: str | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if org:
        headers["X-Organization-Id"] = org
    req = urllib.request.Request(API + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {}


PASSWORDS: dict[str, str] = {}


def sign_in(email: str, password: str, organization: str | None = None) -> str:
    body = {"email": email, "password": password, **({"organization": organization} if organization else {})}
    status, out = call("POST", "/auth/login", body=body)
    if status != 200:
        raise RuntimeError(f"sign-in failed for {email}: {status} {out.get('detail')}")
    token = out["access_token"]
    if out.get("user", {}).get("must_change_password"):
        fresh = secrets.token_urlsafe(18)
        status, _ = call("POST", "/auth/change-password", token,
                         {"current_password": password, "new_password": fresh})
        if status != 200:
            raise RuntimeError(f"password change failed for {email}: {status}")
        return sign_in(email, fresh, organization)
    PASSWORDS[email] = password
    return token


def served_org(token: str, org: str | None = None) -> str | None:
    status, out = call("POST", f"/snapshots/{PROBE[0]}/query", token, PROBE[1], org=org)
    return out.get("organization_id") if status == 200 else f"HTTP {status}"


def start_api(tmp: Path, admin_password: str) -> subprocess.Popen:
    subprocess.run(["psql", "-h", "localhost", "-p", "5433", "-U", "originba", "-d", "postgres", "-qc",
                    f"drop database if exists {STATE_DB}"], env={**os.environ, "PGPASSWORD": "originba"}, check=True)
    subprocess.run(["psql", "-h", "localhost", "-p", "5433", "-U", "originba", "-d", "postgres", "-qc",
                    f"create database {STATE_DB}"], env={**os.environ, "PGPASSWORD": "originba"}, check=True)
    subprocess.run(["psql", "-h", "localhost", "-p", "5433", "-U", "originba", "-d", STATE_DB, "-qf",
                    str(ROOT / "deploy" / "supabase" / "001_init.sql")],
                   env={**os.environ, "PGPASSWORD": "originba"}, check=True, capture_output=True)
    env = {**os.environ,
           "ENVIRONMENT": "development",
           "PORTAL_AUTH_DISABLED": "false",
           "PORTAL_AUTH_DATABASE_URL": f"sqlite:///{tmp / 'auth.db'}",
           "PORTAL_STATE_DATABASE_URL": STATE_URL,
           "PORTAL_AUTH_SECRET": secrets.token_hex(32),
           "PORTAL_BOOTSTRAP_ADMIN_PASSWORD": admin_password,
           "WAREHOUSE_DATABASE_URL_DEMO25": "postgresql://chase@localhost:5432/originba_v2_demo25"}
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "api.app:app", "--host", "127.0.0.1",
                             "--port", str(PORT)], cwd=ROOT, env=env,
                            stdout=open(tmp / "api.log", "w"), stderr=subprocess.STDOUT)
    for _ in range(120):
        try:
            urllib.request.urlopen(API + "/health", timeout=2)
            return proc
        except OSError:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError(f"API did not start; see {tmp / 'api.log'}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="isolation_"))
    admin_pw = secrets.token_urlsafe(18)
    proc = start_api(tmp, admin_pw)
    try:
        admin = sign_in("admin@origin.local", admin_pw)
        users = {}
        for key, role, org in (("ell_user", "user", HOME), ("ell_editor", "editor", HOME),
                               ("demo_user", "user", OTHER)):
            pw = secrets.token_urlsafe(18)
            status, _ = call("POST", "/auth/users", admin, {
                "email": f"{key}@isolation.test", "display_name": key, "password": pw,
                "role": role, "organization_id": org})
            if status != 200:
                raise RuntimeError(f"admin could not create {key}: {status}")
            users[key] = sign_in(f"{key}@isolation.test", pw)
        u, e, d = users["ell_user"], users["ell_editor"], users["demo_user"]

        print("\nA client user reads their own client, whatever they ask for")
        check(served_org(u) == HOME, f"the Ellensburg user is served {HOME}")
        check(served_org(u, org=OTHER) == HOME, "asking for Demo 25 by header still serves Ellensburg")
        check(served_org(d) == OTHER, "the Demo 25 user is served demo25")
        check(served_org(d, org=HOME) == OTHER, "asking for Ellensburg by header still serves Demo 25")
        status, _ = call("POST", "/auth/login", body={"email": "ell_user@isolation.test",
                                                      "password": PASSWORDS["ell_user@isolation.test"],
                                                      "organization": OTHER})
        check(status == 403, "signing in at another client's address is refused, right password or not")

        print("\nA client user cannot administer anything")
        for path, method, body in (("/auth/users", "GET", None), ("/auth/groups", "GET", None),
                                   ("/auth/audit-log", "GET", None),
                                   ("/auth/users", "POST", {"email": "x@isolation.test", "display_name": "xx",
                                                            "password": "y" * 12, "role": "admin"})):
            check(call(method, path, u)[0] == 403, f"user: {method} {path} is refused")
            check(call(method, path, e)[0] == 403, f"editor: {method} {path} is refused")

        print("\nSaved work stays inside its client")
        view = {"snapshot_id": PROBE[0], "snapshot_label": "Customer accounts", "title": "Isolation check",
                "kind": "explorer", "measure_field": "*", "measure_agg": "count"}
        check(call("POST", "/portal/saved-views", u, view)[0] == 403, "a user cannot save a view")
        status, saved = call("POST", "/portal/saved-views", e, view)
        check(status == 200, "an editor saves a view")
        vid = saved.get("id")
        _, mine = call("GET", "/portal/saved-views", u)
        _, theirs = call("GET", "/portal/saved-views", d)
        ids = lambda out: {v.get("id") for v in out.get("views", [])}
        check(vid in ids(mine), "the Ellensburg user sees the Ellensburg view")
        check(vid not in ids(theirs), "the Demo 25 user does not")
        check(call("DELETE", f"/portal/saved-views/{vid}", d)[0] in (403, 404),
              "the Demo 25 user cannot delete it")

        print("\nThe root admin crosses clients, and only by choosing to")
        check(served_org(admin, org=HOME) == HOME, "admin switched to Ellensburg is served Ellensburg")
        check(served_org(admin, org=OTHER) == OTHER, "admin switched to Demo 25 is served Demo 25")
        check(served_org(admin, org="not_a_client") != "not_a_client", "an unknown client is never used")
        status, listed = call("GET", "/auth/users", admin)
        check(status == 200 and len(listed) >= 4, "admin manages users")
    finally:
        proc.terminate()
        proc.wait(timeout=10)
    failed = [label for ok, label in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)} of {len(RESULTS)} boundaries held"
          + ("" if not failed else f"; FAILED: {failed}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
