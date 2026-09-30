"""An auth write is saved before the caller hears it succeeded.

FastAPI (0.118+) runs the exit code of a `yield` dependency AFTER the response is sent,
unless the dependency is declared scope="function". The auth routes commit in that exit
code, so "200 OK" on a password change could reach the caller before the new password
was saved: signing in with it straight away failed (401), found by
scripts/check_tenant_isolation.py (2026-09-30). The same held for creating and updating
users and groups. TestClient cannot show the race (it waits for the whole ASGI call), so
this pins the declaration on every route that takes the session.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PORTAL_AUTH_DISABLED", "false")
os.environ.setdefault("PORTAL_AUTH_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "test-bootstrap-admin-pw")

from fastapi.routing import APIRoute  # noqa: E402

from api.auth import routes as auth_routes  # noqa: E402


def _session_dependencies(dependant):
    for dep in dependant.dependencies:
        if dep.call is auth_routes._db_session:
            yield dep
        yield from _session_dependencies(dep)


def test_every_auth_session_commits_before_the_response():
    late = []
    for route in auth_routes.router.routes:
        if not isinstance(route, APIRoute):
            continue
        for dep in _session_dependencies(route.dependant):
            if dep.scope != "function":
                late.append(f"{sorted(route.methods)} {route.path}")
    assert late == []


def test_the_writes_are_covered():
    paths = {r.path for r in auth_routes.router.routes if isinstance(r, APIRoute)
             and any(True for _ in _session_dependencies(r.dependant))}
    assert {"/auth/change-password", "/auth/users", "/auth/users/{user_id}", "/auth/groups"} <= paths
