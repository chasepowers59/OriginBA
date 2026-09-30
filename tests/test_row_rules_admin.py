"""An administrator sets a user's row rules; the rules are checked and travel with the user.

See tests/test_row_security.py for enforcement. Here: the update validates the rules,
refuses them on an administrator (who sees every row by definition), stores them, and the
user's public record and the audit trail carry them.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory, temporary_engine  # noqa: E402
from api.auth.service import AuthError, create_user, update_user  # noqa: E402

WATER = [{"field": "Service Type", "values": ["Water"]}]


class RowRulesAdminTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"PORTAL_AUTH_DISABLED": "false",
                                                "PORTAL_AUTH_DATABASE_URL": f"sqlite:///{self.tmp.name}/a.db",
                                                "PORTAL_BOOTSTRAP_ADMIN_PASSWORD": "test-bootstrap-admin-pw"})
        self.env.start()
        self.engine = temporary_engine()
        self.engine.__enter__()
        init_auth_database()
        self.session = get_session_factory()()

    def tearDown(self):
        self.session.close()
        self.engine.__exit__(None, None, None)
        self.env.stop()
        self.tmp.cleanup()

    def _user(self, email, role="editor", org="dev"):
        return create_user(self.session, "admin", {"email": email, "display_name": email.split("@")[0],
                                                   "password": "Test-Password-123!", "role": role,
                                                   "organization_id": org})

    def test_rules_are_stored_and_returned(self):
        u = self._user("analyst@utility.gov")
        out = update_user(self.session, "admin", "root", u["id"], {"row_rules": WATER})
        self.assertEqual(out["row_rules"], WATER)
        cleared = update_user(self.session, "admin", "root", u["id"], {"row_rules": []})
        self.assertEqual(cleared["row_rules"], [])

    def test_a_malformed_rule_is_refused(self):
        u = self._user("analyst2@utility.gov")
        with self.assertRaises(AuthError):
            update_user(self.session, "admin", "root", u["id"], {"row_rules": [{"field": "Service Type", "values": []}]})

    def test_an_administrator_cannot_be_restricted(self):
        a = self._user("platform@utility.gov", role="admin", org=None)
        with self.assertRaises(AuthError) as err:
            update_user(self.session, "admin", "root", a["id"], {"row_rules": WATER})
        self.assertIn("every row", str(err.exception))


if __name__ == "__main__":
    unittest.main()
