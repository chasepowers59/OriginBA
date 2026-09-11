"""Is an admin bound to one client, or to all of them? Settled here, with tests.

THE FINDING (2026-09-02). The Users & access panel invites you to create an admin
bound to a single client -- the role dropdown offers Admin, the organization dropdown
labels its blank option "Platform admin", and the help text says "Assign each user to
one client environment". That labelling implies an isolation boundary. The backend
does not implement one:

  GET  /auth/users        filters on client_id (ONE value for the whole deployment,
                          load_portal_config()["client_id"]) -- never organization_id
  GET  /auth/groups       same
  GET  /auth/organizations returns the full client roster
  PUT  /auth/users/{id}   no check that the target is in the actor's organization
  X-Organization-Id       _resolve_active_organization gates on role == "admin" ALONE,
                          so an org-bound admin reads any tenant's warehouse

So an "admin for CityCorp" would in fact be a deployment-wide superuser over all nine
tenants. Measured on the live auth database the same day: the only admin is
admin@origin.local with organization_id = None, so this was latent, not breached.

WHICH MODEL IS RIGHT is answered by the code that already exists, not by preference:

  * _validate_organization_id makes an organization OPTIONAL for role admin and
    REQUIRED for every other role -- admins are meant to have none.
  * data_source_routes._target_organization_id already refuses cross-org work to
    anyone carrying a home org, admin included.

Both only make sense if admin means platform admin. So the invariant is now explicit
and enforced: an admin has NO organization, and role == "admin" therefore already
means platform-wide. That also removes the contradiction between the two functions
above -- an admin has no ctx.organization_id, so the data-source check permits them
and the tenant switch permits them, for the same reason.

A genuine per-client admin tier remains possible later, but it is a feature with a
schema cost (portal_access_groups and portal_audit_log have no organization_id, so a
client admin would read every tenant's groups and audit trail), not something to be
had by accident from a dropdown.

The second class of test here is the one the security skill names as missing outright:
"_resolve_active_organization -- the most isolation-critical function -- has ZERO
tests. No test anywhere sends X-Organization-Id."
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("PORTAL_AUTH_DISABLED", "false")
os.environ.setdefault("PORTAL_AUTH_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "test-bootstrap-admin-pw")

from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory  # noqa: E402
from api.auth.dependencies import _resolve_active_organization  # noqa: E402
from api.auth.service import AuthError, create_user, update_user  # noqa: E402


class AdminHasNoOrganizationTests(unittest.TestCase):
    """The invariant: role == "admin" implies organization_id is None."""

    def setUp(self) -> None:
        init_auth_database()
        self.session = get_session_factory()()
        self.addCleanup(self.session.close)

    def _create(self, email: str, role: str, org: str | None) -> dict:
        return create_user(self.session, "admin", {
            "email": email,
            "display_name": email.split("@")[0],
            "password": "Test-Password-123!",
            "role": role,
            "organization_id": org,
        })

    def test_cannot_create_an_admin_bound_to_a_client(self):
        with self.assertRaises(AuthError) as caught:
            self._create("citycorp.admin@x.gov", "admin", "citycorp")
        # The message has to say what to do instead, or someone just retries.
        self.assertIn("editor", str(caught.exception).lower())

    def test_platform_admin_still_creates(self):
        created = self._create("platform@x.gov", "admin", None)
        self.assertEqual(created["role"], "admin")
        self.assertIsNone(created["organization_id"])

    def test_other_roles_still_require_an_organization(self):
        with self.assertRaises(AuthError):
            self._create("noorg@x.gov", "editor", None)
        self.assertEqual(self._create("ok@x.gov", "editor", "citycorp")["organization_id"], "citycorp")

    def test_promoting_an_org_bound_user_to_admin_is_refused(self):
        """The panel's role dropdown sends only {role}, so organization_id never
        reaches _validate_organization_id and the old org survived the promotion --
        this is the path that actually produced the forbidden account."""
        editor = self._create("promote.me@x.gov", "editor", "citycorp")
        with self.assertRaises(AuthError):
            update_user(self.session, "admin", "someone-else", editor["id"], {"role": "admin"})

    def test_promoting_while_clearing_the_organization_is_allowed(self):
        editor = self._create("promote.ok@x.gov", "editor", "citycorp")
        promoted = update_user(self.session, "admin", "someone-else", editor["id"],
                               {"role": "admin", "organization_id": None})
        self.assertEqual(promoted["role"], "admin")
        self.assertIsNone(promoted["organization_id"])

    def test_cannot_bind_an_existing_admin_to_a_client(self):
        admin = self._create("bindme@x.gov", "admin", None)
        with self.assertRaises(AuthError):
            update_user(self.session, "admin", "someone-else", admin["id"],
                        {"organization_id": "odessa"})

    def test_demoting_an_admin_still_requires_an_organization(self):
        admin = self._create("demote@x.gov", "admin", None)
        with self.assertRaises(AuthError):
            update_user(self.session, "admin", "someone-else", admin["id"], {"role": "editor"})
        demoted = update_user(self.session, "admin", "someone-else", admin["id"],
                              {"role": "editor", "organization_id": "odessa"})
        self.assertEqual(demoted["organization_id"], "odessa")


class ActiveOrganizationHeaderTests(unittest.TestCase):
    """X-Organization-Id, which had no test of any kind before this file.

    The header chooses among configured tenants for an admin. For anyone else it is
    IGNORED rather than rejected -- deliberately, so a probe cannot learn the header
    does anything -- and an unregistered value is discarded so it can never reach a
    connection string or a catalog path.
    """

    def test_a_non_admin_cannot_switch_tenants(self):
        for role in ("user", "editor"):
            self.assertIsNone(_resolve_active_organization(role, "ellensburg"), role)

    def test_a_non_admin_is_ignored_not_rejected(self):
        # Returning None (use your own org) rather than raising is the fail-safe.
        self.assertIsNone(_resolve_active_organization("user", "citycorp"))

    def test_an_admin_may_switch_to_a_registered_tenant(self):
        self.assertEqual(_resolve_active_organization("admin", "ellensburg"), "ellensburg")

    def test_an_unregistered_organization_is_discarded(self):
        for bogus in ("../../etc/passwd", "postgres://evil/db", "not_a_client", "'; DROP TABLE"):
            self.assertIsNone(_resolve_active_organization("admin", bogus), bogus)

    def test_absent_header_resolves_to_nothing(self):
        self.assertIsNone(_resolve_active_organization("admin", None))
        self.assertIsNone(_resolve_active_organization("admin", ""))

    def test_an_unknown_role_cannot_switch(self):
        self.assertIsNone(_resolve_active_organization("superuser", "ellensburg"))
        self.assertIsNone(_resolve_active_organization("", "ellensburg"))


class EffectiveOrganizationTests(unittest.TestCase):
    """effective_organization_id() is what every data route resolves against."""

    def _ctx(self, **kw):
        from api.auth.dependencies import AuthContext
        base = dict(id="u", email="e@x.gov", display_name="E", role="user",
                    client_id="demo", organization_id=None, organization_name=None,
                    permissions=set(), workstreams=["*"])
        base.update(kw)
        return AuthContext(**base)

    def test_a_switched_tenant_wins_over_the_home_org(self):
        ctx = self._ctx(role="admin", organization_id=None, active_organization_id="odessa")
        self.assertEqual(ctx.effective_organization_id(), "odessa")

    def test_a_user_gets_their_own_org(self):
        self.assertEqual(self._ctx(organization_id="citycorp").effective_organization_id(), "citycorp")

    def test_no_org_and_no_switch_is_refused_at_the_data_edge(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            self._ctx().require_organization()
        self.assertEqual(caught.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
