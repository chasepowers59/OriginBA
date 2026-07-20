#!/usr/bin/env python3
"""Smoke test portal auth: login, admin CRUD, role permissions, scoping."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

API = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_EMAIL = os.getenv("PORTAL_BOOTSTRAP_ADMIN_EMAIL", "admin@origin.local")
ADMIN_PASSWORD = os.getenv("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe-Admin-1!")


def request(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict | list]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read().decode()
            return resp.status, json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode()
        try:
            parsed = json.loads(payload) if payload else {"detail": exc.reason}
        except json.JSONDecodeError:
            parsed = {"detail": payload or exc.reason}
        return exc.code, parsed


def assert_ok(label: str, status: int, expected: int = 200) -> None:
    if status != expected:
        raise SystemExit(f"FAIL {label}: HTTP {status} (expected {expected})")
    print(f"  ok {label}")


def main() -> None:
    print(f"Portal auth smoke test against {API}")

    status, data = request("GET", "/auth/status")
    assert_ok("auth status", status)
    if not data.get("enabled"):
        raise SystemExit("FAIL: auth should be enabled")

    status, login = request(
        "POST",
        "/auth/login",
        body={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert_ok("admin login", status)
    token = login.get("access_token")
    if not token:
        raise SystemExit("FAIL: login missing access_token")

    status, me = request("GET", "/auth/me", token=token)
    assert_ok("auth me", status)
    admin_id = me.get("id")
    perms = set(me.get("permissions") or [])
    for required in ("users:manage", "groups:manage", "snapshots:raw_sql"):
        if required not in perms:
            raise SystemExit(f"FAIL: admin missing permission {required}")

    status, groups = request("GET", "/auth/groups", token=token)
    assert_ok("list groups", status)
    group_name = "smoke-finance"
    existing = next((g for g in groups if g.get("name") == group_name), None)
    if existing:
        group_id = existing["id"]
    else:
        status, created = request(
            "POST",
            "/auth/groups",
            token=token,
            body={
                "name": group_name,
                "description": "Smoke test finance access",
                "workstreams": ["finance", "billing"],
            },
        )
        assert_ok("create group", status)
        group_id = created["id"]

    editor_email = "editor.smoke@origin.local"
    status, users = request("GET", "/auth/users", token=token)
    assert_ok("list users", status)
    editor = next((u for u in users if u.get("email") == editor_email), None)
    if editor:
        editor_id = editor["id"]
        if group_id not in (editor.get("group_ids") or []):
            status, _ = request(
                "PUT",
                f"/auth/users/{editor_id}",
                token=token,
                body={"group_ids": [group_id]},
            )
            assert_ok("assign editor group", status)
    else:
        status, created = request(
            "POST",
            "/auth/users",
            token=token,
            body={
                "email": editor_email,
                "password": "Editor-Smoke-1!",
                "display_name": "Smoke Editor",
                "role": "editor",
                "group_ids": [group_id],
            },
        )
        assert_ok("create editor user", status)
        editor_id = created["id"]

    user_email = "user.smoke@origin.local"
    portal_user = next((u for u in users if u.get("email") == user_email), None)
    if not portal_user:
        status, _ = request(
            "POST",
            "/auth/users",
            token=token,
            body={
                "email": user_email,
                "password": "User-Smoke-1!",
                "display_name": "Smoke User",
                "role": "user",
                "group_ids": [group_id],
            },
        )
        assert_ok("create basic user", status)

    status, editor_login = request(
        "POST",
        "/auth/login",
        body={"email": editor_email, "password": "Editor-Smoke-1!"},
    )
    assert_ok("editor login", status)
    editor_token = editor_login["access_token"]

    status, editor_me = request("GET", "/auth/me", token=editor_token)
    assert_ok("editor me", status)
    if "users:manage" in set(editor_me.get("permissions") or []):
        raise SystemExit("FAIL: editor should not have users:manage")
    ws = set(editor_me.get("workstreams") or [])
    if not ws <= {"finance", "billing"} or ws == {"*"}:
        raise SystemExit(f"FAIL: unexpected editor workstreams {ws}")

    status, denied = request("GET", "/auth/users", token=editor_token)
    if status != 403:
        raise SystemExit(f"FAIL: editor should be denied user list, got {status}")
    print("  ok editor denied user management")

    status, _ = request("GET", "/snapshots")
    if status != 401:
        raise SystemExit(f"FAIL: unauthenticated snapshots should 401, got {status}")

    status, catalog = request("GET", "/snapshots", token=editor_token)
    assert_ok("editor snapshots", status)
    snap_count = len(catalog.get("snapshots") or [])
    ws_count = len(catalog.get("workstreams") or [])
    print(f"  editor sees {snap_count} snapshots, {ws_count} workstreams")

    status, exec_sum = request("GET", "/snapshots/executive-summary?days=30", token=editor_token)
    assert_ok("editor executive summary", status)
    kpi_ws = {k.get("workstream") for k in exec_sum.get("kpis") or []}
    if not kpi_ws <= {"finance", "billing"}:
        raise SystemExit(f"FAIL: executive KPIs not scoped: {kpi_ws}")
    print(f"  editor executive KPIs scoped ({len(exec_sum.get('kpis') or [])} tiles)")

    status, ds = request("GET", "/portal/data-source", token=editor_token)
    assert_ok("editor data-source status", status)
    if "user_masked" in ds or "dsn_masked" in ds:
        raise SystemExit("FAIL: editor should not see masked connection details")
    print("  ok editor data-source redacted")

    status, nlq = request("GET", "/portal/analytics-nlq/metrics", token=editor_token)
    assert_ok("editor nlq metrics", status)
    admin_nlq = request("GET", "/portal/analytics-nlq/metrics", token=token)[1]
    if len(nlq.get("metrics") or []) >= len(admin_nlq.get("metrics") or []):
        raise SystemExit("FAIL: editor NLQ catalog should be narrower than admin")
    print(f"  editor NLQ metrics scoped ({len(nlq.get('metrics') or [])} of {len(admin_nlq.get('metrics') or [])})")

    status, ulogin = request("POST", "/auth/login", body={"email": user_email, "password": "User-Smoke-1!"})
    assert_ok("user login", status)
    user_token = ulogin["access_token"]
    status, ume = request("GET", "/auth/me", token=user_token)
    assert_ok("user me", status)
    if "explorer:builder" in set(ume.get("permissions") or []):
        raise SystemExit("FAIL: basic user should not have builder permission")

    status, self_demote = request(
        "PUT",
        f"/auth/users/{admin_id}",
        token=token,
        body={"role": "editor"},
    )
    if status != 400:
        raise SystemExit(f"FAIL: admin self-demotion should 400, got {status}")
    print("  ok admin self-demotion blocked")

    status, pending_login = request(
        "POST",
        "/auth/users",
        token=token,
        body={
            "email": "pending.smoke@origin.local",
            "password": "Pending-Smoke-1!",
            "display_name": "Pending Password",
            "role": "user",
            "group_ids": [group_id],
        },
    )
    if status == 200:
        status, pending = request(
            "POST",
            "/auth/login",
            body={"email": "pending.smoke@origin.local", "password": "Pending-Smoke-1!"},
        )
        assert_ok("pending-password login", status)
        pending_token = pending["access_token"]
        if not pending.get("user", {}).get("must_change_password"):
            raise SystemExit("FAIL: new user should require password change")
        status, blocked = request("GET", "/snapshots", token=pending_token)
        if status != 403:
            raise SystemExit(f"FAIL: pending password user should be blocked from snapshots, got {status}")
        status, changed = request(
            "POST",
            "/auth/change-password",
            token=pending_token,
            body={"current_password": "Pending-Smoke-1!", "new_password": "Pending-Smoke-2!"},
        )
        assert_ok("change password", status)
        status, after = request("GET", "/snapshots", token=pending_token)
        assert_ok("snapshots after password change", status)
        print("  ok password-change gate")

    print("\nAll portal auth smoke checks passed.")


if __name__ == "__main__":
    main()
