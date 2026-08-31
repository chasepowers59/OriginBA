"""Portal identity and RBAC tests."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["PORTAL_AUTH_DISABLED"] = "true"
os.environ["PORTAL_AUTH_DATABASE_URL"] = "sqlite:///:memory:"

from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory  # noqa: E402
from api.auth.permissions import permissions_for_role, role_at_least  # noqa: E402
from api.auth.security import hash_password, verify_password  # noqa: E402
from api.auth.service import AuthError, create_group, create_user, get_user, update_user, user_to_public  # noqa: E402
from api.executive_dashboard import build_executive_summary  # noqa: E402
from api.organizations import (  # noqa: E402
    is_valid_org_id,
    list_organizations_public,
    organization_display_name,
    resolve_organization,
)


class PortalAuthTests(unittest.TestCase):
    def test_password_hash_roundtrip(self) -> None:
        encoded = hash_password("Test-Password-123!")
        self.assertTrue(verify_password("Test-Password-123!", encoded))
        self.assertFalse(verify_password("wrong", encoded))

    def test_role_hierarchy_permissions(self) -> None:
        user_perms = permissions_for_role("user")
        editor_perms = permissions_for_role("editor")
        admin_perms = permissions_for_role("admin")

        self.assertIn("snapshots:query", user_perms)
        self.assertNotIn("dashboards:write", user_perms)

        self.assertIn("dashboards:write", editor_perms)
        self.assertIn("snapshots:query", editor_perms)
        self.assertNotIn("users:manage", editor_perms)

        self.assertIn("users:manage", admin_perms)
        self.assertIn("snapshots:raw_sql", admin_perms)

    def test_role_at_least(self) -> None:
        self.assertTrue(role_at_least("admin", "editor"))
        self.assertTrue(role_at_least("editor", "user"))
        self.assertFalse(role_at_least("user", "editor"))

    def test_organization_registry(self) -> None:
        orgs = list_organizations_public()
        # Assert the known tenants are present rather than a brittle exact count that
        # drifts every time a client is onboarded.
        ids = {o["id"] for o in orgs}
        self.assertGreaterEqual(len(orgs), 6)
        self.assertIn("ellensburg", ids)
        self.assertIn("dev", ids)
        self.assertTrue(is_valid_org_id("ellensburg"))
        self.assertFalse(is_valid_org_id("unknown-client"))

    def test_resolve_organization_by_id_and_name(self) -> None:
        # Multi-tenant login accepts the slug (from a /<slug> URL) or the typed display
        # name, both case-insensitively; unknown/blank tokens resolve to None.
        self.assertEqual(resolve_organization("ellensburg")["id"], "ellensburg")
        self.assertEqual(resolve_organization("ELLENSBURG")["id"], "ellensburg")
        by_name = resolve_organization(organization_display_name("dev"))
        self.assertEqual(by_name["id"], "dev")
        self.assertIsNone(resolve_organization("unknown-client"))
        self.assertIsNone(resolve_organization(None))
        self.assertIsNone(resolve_organization("   "))

    def test_user_requires_organization_for_non_admin(self) -> None:
        init_auth_database()
        factory = get_session_factory()
        with factory() as session:
            with self.assertRaises(AuthError):
                create_user(
                    session,
                    "admin",
                    {
                        "email": "no-org@origin.local",
                        "display_name": "No Org",
                        "password": "No-Org-User-1!",
                        "role": "user",
                        "group_ids": [],
                    },
                )

    def test_user_group_assignment_persists(self) -> None:
        init_auth_database()
        factory = get_session_factory()
        with factory() as session:
            group = create_group(
                session,
                {
                    "name": "Finance only",
                    "description": "test",
                    "workstreams": ["finance"],
                },
            )
            session.commit()
            group_id = group["id"]

        with factory() as session:
            created = create_user(
                session,
                "admin",
                {
                    "email": "scoped@origin.local",
                    "display_name": "Scoped User",
                    "password": "Scoped-User-1!",
                    "role": "user",
                    "organization_id": "ellensburg",
                    "group_ids": [group_id],
                },
            )
            session.commit()
            user_id = created["id"]
            self.assertEqual(created["workstreams"], ["finance"])
            self.assertEqual(created["group_ids"], [group_id])

        with factory() as session:
            reloaded = user_to_public(get_user(session, user_id))
            self.assertEqual(reloaded["workstreams"], ["finance"])
            self.assertEqual(reloaded["group_ids"], [group_id])

    def test_executive_summary_workstream_scoping(self) -> None:
        all_kpis = build_executive_summary(30, allowed_workstreams=["*"])["kpis"]
        scoped = build_executive_summary(30, allowed_workstreams=["finance", "billing"])["kpis"]
        self.assertLess(len(scoped), len(all_kpis))
        for kpi in scoped:
            self.assertIn(kpi.get("workstream"), {"finance", "billing"})

    def test_admin_self_lockout_guards(self) -> None:
        init_auth_database()
        factory = get_session_factory()
        with factory() as session:
            admin = create_user(
                session,
                "admin",
                {
                    "email": "solo-admin@origin.local",
                    "display_name": "Solo Admin",
                    "password": "Solo-Admin-1!",
                    "role": "admin",
                    "group_ids": [],
                },
            )
            session.commit()
            admin_id = admin["id"]
        with factory() as session:
            with self.assertRaises(AuthError):
                update_user(session, "admin", admin_id, admin_id, {"is_active": False})
            with self.assertRaises(AuthError):
                update_user(session, "admin", admin_id, admin_id, {"role": "editor"})


if __name__ == "__main__":
    unittest.main()


class ExecutiveCatalogAvailabilityTests(unittest.TestCase):
    """A legacy-catalog org (demo: cisadm snapshots) has none of the dbt canvases the
    executive KPIs read, so the dashboard must SKIP them with one clear note — never
    render a grid of 'Unknown snapshot' errors."""

    def test_dbt_org_has_all_kpis(self) -> None:
        from api.executive_dashboard import EXECUTIVE_KPIS, available_kpis
        avail, note = available_kpis(EXECUTIVE_KPIS, "dev")
        self.assertEqual(len(avail), len(EXECUTIVE_KPIS))
        self.assertIsNone(note)

    def test_legacy_catalog_org_skips_all_with_note(self) -> None:
        from api.executive_dashboard import EXECUTIVE_KPIS, available_kpis
        avail, note = available_kpis(EXECUTIVE_KPIS, "demo")
        self.assertEqual(avail, [])
        self.assertIsNotNone(note)
        self.assertIn("canvas", note.lower())
