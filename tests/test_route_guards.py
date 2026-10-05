"""Every API route is guarded, and a new route cannot ship without saying how (2026-10-05).

Rule 6 of the security model ("permissions gate every data route") was enforced route by
route; nothing stopped a new route from shipping with no check. This walks the app's own
route table: each route is either on PUBLIC with its reason, or SESSION_ONLY (a signed-in
person acting on their own account), or it authenticates AND gates on a permission or role,
directly, through a dependency, or through a named gate helper. A route that is none of
these fails here before it reaches a client.
"""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from api.app import app  # noqa: E402

PUBLIC = {
    ("POST", "/auth/login"): "signing in",
    ("GET", "/auth/status"): "whether sign-in is on, for the login page",
    ("GET", "/auth/tenants/{slug}"): "a client's sign-in branding, before sign-in",
    ("GET", "/auth/oidc/login"): "starting SSO",
    ("GET", "/auth/oidc/callback"): "SSO return; the destination comes from server config",
    ("GET", "/health"): "liveness; admin detail only behind auth (audit M3)",
    ("GET", "/embed/{token}/data"): "an embed link: the signed, expiring token IS the credential",
}
SESSION_ONLY = {
    ("GET", "/auth/me"): "who am I",
    ("POST", "/auth/change-password"): "my own password, including the forced first change",
}
# Gates applied inside the endpoint or a helper it calls, named so they are reviewed.
GATE_HELPERS = ("require_permission", "_assistant_for", "_require_data_source_manage", 'ctx.role != "admin"')


def _dependency_names(dependant) -> set[str]:
    names: set[str] = set()
    for d in dependant.dependencies:
        names.add(getattr(d.call, "__qualname__", getattr(d.call, "__name__", repr(d.call))))
        names |= _dependency_names(d)
    return names


def _routes(application=app):
    for r in application.routes:
        if isinstance(r, APIRoute):
            for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
                yield (m, r.path), r


def unguarded_routes(application=app) -> list[str]:
    unguarded = []
    for key, route in _routes(application):
        if key in PUBLIC:
            continue
        names = _dependency_names(route.dependant)
        if key in SESSION_ONLY:
            if not any("auth_context" in n for n in names):
                unguarded.append(f"{key}: session-only route with no session context")
            continue
        authenticated = any("get_auth_context" in n or "require_permission" in n for n in names)
        source = inspect.getsource(route.endpoint)
        gated = (any("require_permission" in n or "_require_data_source_manage" in n for n in names)
                 or any(g in source for g in GATE_HELPERS))
        if not (authenticated and gated):
            unguarded.append(f"{key}: authenticated={authenticated} gated={gated}")
    return unguarded


class RouteGuards(unittest.TestCase):
    def test_every_route_is_public_by_name_or_guarded(self):
        unguarded = unguarded_routes()
        self.assertEqual(unguarded, [], "routes without a guard:\n  " + "\n  ".join(unguarded))

    def test_the_check_catches_an_unguarded_route(self):
        from fastapi import Depends, FastAPI

        from api.auth.dependencies import AuthContext, get_auth_context

        planted = FastAPI()

        @planted.get("/leaky")
        def leaky(ctx: AuthContext = Depends(get_auth_context)):   # signed in, but no permission
            return {}

        @planted.get("/open")
        def wide_open():
            return {}

        found = unguarded_routes(planted)
        self.assertEqual(len(found), 2, found)

    def test_the_public_list_names_only_real_routes(self):
        real = {key for key, _ in _routes()}
        self.assertEqual(sorted(set(PUBLIC) - real), [], "PUBLIC names a route that no longer exists")
        self.assertEqual(sorted(set(SESSION_ONLY) - real), [], "SESSION_ONLY names a route that no longer exists")

    def test_a_route_reading_an_organization_from_the_request_is_refused(self):
        # Rule 1: the organization comes from the auth context. A route whose own parameters
        # carry an organization would let the caller choose; none may, except the admin's
        # data-source management, which validates against the registry and refuses cross-org.
        allowed = {("GET", "/portal/data-source"), ("PUT", "/portal/data-source"),
                   ("DELETE", "/portal/data-source"), ("POST", "/portal/data-source/test")}
        offenders = []
        for key, route in _routes():
            params = [p.name for p in route.dependant.query_params + route.dependant.path_params]
            if any(p in ("organization_id", "org", "org_id", "client_id", "tenant") for p in params) and key not in allowed:
                offenders.append(f"{key}: {params}")
        self.assertEqual(offenders, [], "routes taking an organization from the request:\n  " + "\n  ".join(offenders))


if __name__ == "__main__":
    unittest.main()
