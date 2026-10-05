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
THIRD = "citycorp"   # the store checks below need no warehouse: they hold with the VPN down
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
                               ("ell_admin", "client_admin", HOME), ("demo_user", "user", OTHER),
                               ("cc_user", "user", THIRD), ("cc_editor", "editor", THIRD)):
            pw = secrets.token_urlsafe(18)
            status, _ = call("POST", "/auth/users", admin, {
                "email": f"{key}@isolation.test", "display_name": key, "password": pw,
                "role": role, "organization_id": org})
            if status != 200:
                raise RuntimeError(f"admin could not create {key}: {status}")
            users[key] = sign_in(f"{key}@isolation.test", pw)
        u, e, d, ca = users["ell_user"], users["ell_editor"], users["demo_user"], users["ell_admin"]

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

        print("\nA client admin administers their own client and no other")
        check(served_org(ca, org=OTHER) == HOME, "the Ellensburg client admin cannot switch to Demo 25")
        status, listed = call("GET", "/auth/users", ca)
        check(status == 200 and {x["organization_id"] for x in listed} == {HOME},
              "the client admin sees Ellensburg's users only")
        status, made = call("POST", "/auth/users", ca, {"email": "made@isolation.test", "display_name": "Made",
                                                        "password": secrets.token_urlsafe(18), "role": "user"})
        check(status == 200 and made.get("organization_id") == HOME, "the client admin adds an Ellensburg user")
        status, _ = call("POST", "/auth/users", ca, {"email": "other@isolation.test", "display_name": "Other",
                                                     "password": secrets.token_urlsafe(18), "role": "user",
                                                     "organization_id": OTHER})
        check(status in (400, 403), "the client admin cannot add a Demo 25 user")
        status, _ = call("POST", "/auth/users", ca, {"email": "root2@isolation.test", "display_name": "Root",
                                                     "password": secrets.token_urlsafe(18), "role": "admin"})
        check(status in (400, 403), "the client admin cannot make a platform admin")
        _, everyone = call("GET", "/auth/users", admin)
        demo_id = next(x["id"] for x in everyone if x["email"] == "demo_user@isolation.test")
        check(call("PUT", f"/auth/users/{demo_id}", ca, {"display_name": "Taken"})[0] == 404,
              "the client admin cannot edit a Demo 25 user")
        _, orgs = call("GET", "/auth/organizations", ca)
        check([o["id"] for o in orgs] == [HOME], "the client admin's client list is Ellensburg alone")
        _, trail = call("GET", "/auth/audit-log", ca)
        check({x.get("organization_id") for x in trail} <= {HOME}, "the client admin's audit trail is Ellensburg's")

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

        print("\nEvery stored thing stays inside its client (CityCorp against Ellensburg)")
        cu, ce = users["cc_user"], users["cc_editor"]
        listed_ids = lambda out, key: {x.get("id") for x in (out.get(key) or [])} if isinstance(out, dict) else set()
        # dashboards
        status, board = call("POST", "/portal/dashboards", e, {"title": "Ellensburg board", "days": 30, "tiles": []})
        check(status == 200, "an Ellensburg editor saves a dashboard")
        bid = board.get("id")
        check(call("POST", "/portal/dashboards", cu, {"title": "x", "tiles": []})[0] == 403, "a CityCorp user cannot save a dashboard")
        for org in (None, HOME):
            _, theirs = call("GET", "/portal/dashboards", ce, org=org)
            check(bid not in listed_ids(theirs, "dashboards"),
                  "CityCorp does not list the Ellensburg dashboard" + (" (header forged to Ellensburg)" if org else ""))
        check(call("GET", f"/portal/dashboards/{bid}", ce, org=HOME)[0] == 404, "CityCorp cannot open it by id, header forged")
        check(call("PUT", f"/portal/dashboards/{bid}", ce, {"title": "Taken"}, org=HOME)[0] in (403, 404), "CityCorp cannot change it")
        check(call("DELETE", f"/portal/dashboards/{bid}", ce, org=HOME)[0] in (403, 404), "CityCorp cannot delete it")
        check(call("GET", f"/portal/dashboards/{bid}", e)[0] == 200, "and it is still Ellensburg's afterwards")
        # saved views
        check(call("PATCH", f"/portal/saved-views/{vid}", ce, {"title": "Taken"}, org=HOME)[0] in (403, 404),
              "CityCorp cannot rename the Ellensburg view, header forged")
        _, cc_views = call("GET", "/portal/saved-views", ce, org=HOME)
        check(vid not in ids(cc_views), "CityCorp does not list the Ellensburg view, header forged")
        # notes
        status, note = call("POST", "/annotations", e, {"target_type": "saved_view", "target_id": vid, "text": "Ellensburg note"})
        check(status == 200, "an Ellensburg editor notes the view")
        nid = (note.get("annotation") or note).get("id")
        check(call("GET", f"/annotations?target_type=saved_view&target_id={vid}", ce, org=HOME)[0] == 404,
              "CityCorp cannot read the Ellensburg note")
        check(call("POST", "/annotations", ce, {"target_type": "saved_view", "target_id": vid, "text": "x"}, org=HOME)[0] == 404,
              "CityCorp cannot note the Ellensburg view")
        check(call("DELETE", f"/annotations/{nid}", ce, org=HOME)[0] in (403, 404), "CityCorp cannot delete the Ellensburg note")
        # alerts
        status, alert = call("POST", "/kpi-alerts", e, {"saved_view_id": vid, "condition": "above", "threshold": 1,
                                                        "recipients": ["qa@isolation.test"]})
        check(status == 200, "an Ellensburg editor sets an alert on the view")
        aid = (alert.get("alert") or alert).get("id")
        _, cc_alerts = call("GET", "/kpi-alerts", ce, org=HOME)
        check(aid not in listed_ids(cc_alerts, "alerts"), "CityCorp does not list the Ellensburg alert")
        check(call("DELETE", f"/kpi-alerts/{aid}", ce, org=HOME)[0] in (403, 404), "CityCorp cannot delete it")
        check(call("POST", "/kpi-alerts", ce, {"saved_view_id": vid, "condition": "above", "threshold": 1,
                                               "recipients": ["x@isolation.test"]}, org=HOME)[0] in (400, 403, 404),
              "CityCorp cannot alert on the Ellensburg view")
        # schedules
        status, sched = call("POST", "/report-schedules", e, {"saved_view_id": vid, "recipients": ["qa@isolation.test"]})
        check(status == 200, "an Ellensburg editor schedules the view")
        sid = (sched.get("schedule") or sched).get("id")
        _, cc_scheds = call("GET", "/report-schedules", ce, org=HOME)
        check(sid not in listed_ids(cc_scheds, "schedules"), "CityCorp does not list the Ellensburg schedule")
        check(call("DELETE", f"/report-schedules/{sid}", ce, org=HOME)[0] in (403, 404), "CityCorp cannot delete it")
        check(call("POST", f"/report-schedules/{sid}/run-now", ce, org=HOME)[0] in (403, 404), "CityCorp cannot run it")
        check(call("POST", "/report-schedules", ce, {"saved_view_id": vid, "recipients": ["x@isolation.test"]}, org=HOME)[0]
              in (400, 403, 404), "CityCorp cannot schedule the Ellensburg view")
        # embed links
        check(call("POST", "/portal/embed-tokens", ce, {"view_id": vid}, org=HOME)[0] in (403, 404),
              "CityCorp cannot make an embed link to the Ellensburg view")
        check(call("POST", "/portal/embed-tokens", cu, {"view_id": vid})[0] == 403, "a CityCorp user cannot make embed links")
        # letters and admin surfaces
        status, runs = call("GET", "/portal/letters/runs", ce, org=HOME)
        check(status in (200, 403) and runs.get("organization_id", THIRD) == THIRD,
              "CityCorp's letter runs are CityCorp's, header forged")
        for path in ("/portal/health", "/auth/users", "/auth/audit-log"):
            check(call("GET", path, ce)[0] == 403, f"a CityCorp editor: GET {path} is refused")
        # an editor exports a content pack of their OWN client's shared work, never another's
        status, pack = call("GET", "/portal/content-pack", ce, org=HOME)
        packed = json.dumps(pack)
        check(status == 200 and pack.get("source_organization") == THIRD and vid not in packed and bid not in packed,
              "CityCorp's content pack is CityCorp's alone, header forged")
        status, orgs = call("GET", "/auth/organizations", ce)
        check(status == 403 or [o.get("id") for o in orgs] == [THIRD], "a CityCorp editor sees no other client in the picker")

        print("\nSessions end when they should")
        pw_old = secrets.token_urlsafe(18)
        call("POST", "/auth/users", admin, {"email": "rotate@isolation.test", "display_name": "rotate", "password": pw_old,
                                             "role": "user", "organization_id": THIRD})
        stale = sign_in("rotate@isolation.test", pw_old)          # signs in, and changes the forced first password
        check(call("GET", "/auth/me", stale)[0] == 200, "a fresh token opens a session")
        fresh_pw = secrets.token_urlsafe(18)
        status, changed = call("POST", "/auth/change-password", stale,
                               {"current_password": PASSWORDS["rotate@isolation.test"], "new_password": fresh_pw})
        check(status == 200 and bool(changed.get("access_token")), "a password change returns a fresh token")
        check(call("GET", "/auth/me", stale)[0] == 401, "the token from before the change no longer opens a session")
        check(call("GET", "/auth/me", changed.get("access_token"))[0] == 200, "the fresh token does")
        status, _ = call("POST", "/auth/login", body={"email": "nobody@isolation.test", "password": "wrong-password-1"})
        check(status == 401, "an unknown email is refused like a wrong password")
        _, trail = call("GET", "/auth/audit-log", admin)
        entries = trail if isinstance(trail, list) else trail.get("entries", [])
        actions = {x.get("action") for x in entries}
        check({"login", "login_failed"} <= actions, "sign-ins, failed and successful, are in the audit trail")

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
