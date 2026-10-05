"""Sign-out ends the session on the server, and new passwords meet a policy (2026-10-05).

1. Signing out only cleared the browser: whoever had copied the token kept the session until
   it expired (up to a working day). Every token now carries an id, sign-out records it, and
   a recorded id never opens a session again. Other sessions of the same person continue.
2. A new password needed only 8 characters, so "password" and the person's own email passed.
   A new password now needs 12, may not contain the email, and may not be a common one.
   Existing passwords keep working; the policy applies when one is set.
3. PBKDF2 ran at 260,000 iterations; OWASP's floor is 600,000. New hashes use 600,000 and an
   older hash is upgraded the next time its owner signs in.
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

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.auth import security  # noqa: E402
from api.auth.password_policy import password_problem  # noqa: E402

PW = "Sessions-Test-Pass-1"
ENV = {"PORTAL_AUTH_SECRET": "s" * 64, "PORTAL_BOOTSTRAP_ADMIN_PASSWORD": "bootstrap-admin-password"}


class PasswordPolicy(unittest.TestCase):
    def test_a_short_password_is_refused(self):
        self.assertIn("12 characters", password_problem("Short-pw-1", "ann@example.test"))

    def test_a_password_holding_the_email_is_refused(self):
        self.assertIn("email", password_problem("ann.lee-2026-portal", "ann.lee@example.test"))

    def test_a_common_password_is_refused(self):
        for common in ("password1234", "Password1234", "123456789012", "qwertyuiop12", "aaaaaaaaaaaa"):
            self.assertIsNotNone(password_problem(common, "x@example.test"), common)

    def test_a_long_uncommon_password_passes(self):
        self.assertIsNone(password_problem("correct horse battery staple", "ann@example.test"))


class Hashing(unittest.TestCase):
    def test_new_hashes_use_the_owasp_floor(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertEqual(security.hash_password("x" * 12).split("$")[1], "600000")

    def test_an_older_hash_is_flagged_for_upgrade(self):
        old = "pbkdf2_sha256$260000$00$00"
        self.assertTrue(security.needs_rehash(old))
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertFalse(security.needs_rehash(security.hash_password("y" * 12)))

    def test_tokens_carry_an_id(self):
        with mock.patch.dict(os.environ, ENV):
            a = security.create_access_token(user_id="u", email="e@x.t", role="user", client_id="c",
                                             organization_id=None, workstreams=[], pwv="p")
            b = security.create_access_token(user_id="u", email="e@x.t", role="user", client_id="c",
                                             organization_id=None, workstreams=[], pwv="p")
            ja, jb = security.decode_access_token(a)["jti"], security.decode_access_token(b)["jti"]
        self.assertTrue(ja and jb and ja != jb)


class Sessions(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._db = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        cls._db.close()
        cls._env = mock.patch.dict(os.environ, {**ENV, "PORTAL_AUTH_DATABASE_URL": f"sqlite:///{cls._db.name}"})
        cls._env.start()
        os.environ.pop("PORTAL_AUTH_DISABLED", None)
        from api.auth.database import temporary_engine
        cls._engine = temporary_engine()
        cls._engine.__enter__()
        from api.auth.bootstrap import init_auth_database
        from api.auth.database import get_session_factory
        from api.auth.routes import router
        from api.auth.models import User
        from api.auth.service import create_user
        init_auth_database()
        with get_session_factory()() as session:
            for email, role, org in (("ann@sessions.test", "user", "citycorp"), ("root@sessions.test", "admin", None)):
                create_user(session, "admin", {"email": email, "display_name": email, "password": PW,
                                               "role": role, "organization_id": org})
            session.query(User).update({User.must_change_password: False})
            session.commit()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._engine.__exit__(None, None, None)
        cls._env.stop()
        os.unlink(cls._db.name)

    def sign_in(self, email="ann@sessions.test", password=PW) -> str:
        r = self.client.post("/auth/login", json={"email": email, "password": password})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["access_token"]

    def me(self, token: str) -> int:
        return self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code

    def test_sign_out_ends_that_session_and_only_that_one(self):
        first, second = self.sign_in(), self.sign_in()
        self.assertEqual(self.client.post("/auth/logout", headers={"Authorization": f"Bearer {first}"}).status_code, 200)
        self.assertEqual(self.me(first), 401)
        self.assertEqual(self.me(second), 200)

    def test_sign_out_is_audited(self):
        token = self.sign_in()
        self.client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        root = self.sign_in("root@sessions.test")
        log = self.client.get("/auth/audit-log", headers={"Authorization": f"Bearer {root}"}).json()
        rows = log["entries"] if isinstance(log, dict) else log
        self.assertTrue(any(r.get("action") == "logout" for r in rows))

    def test_sign_out_without_a_session_is_harmless(self):
        self.assertIn(self.client.post("/auth/logout").status_code, (200, 401))

    def test_a_weak_new_password_is_refused_with_the_reason(self):
        token = self.sign_in()
        r = self.client.post("/auth/change-password", headers={"Authorization": f"Bearer {token}"},
                             json={"current_password": PW, "new_password": "password1234"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("common", r.json()["detail"])

    def test_an_admin_cannot_set_a_weak_password_either(self):
        root = self.sign_in("root@sessions.test")
        r = self.client.post("/auth/users", headers={"Authorization": f"Bearer {root}"},
                             json={"email": "weak@sessions.test", "display_name": "Weak Account", "password": "Short-pw-1",
                                   "role": "user", "organization_id": "citycorp"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("12 characters", r.json()["detail"])

    def test_an_older_hash_is_upgraded_at_sign_in(self):
        from api.auth.database import get_session_factory
        from api.auth.models import User
        with get_session_factory()() as session:
            user = session.query(User).filter_by(email="root@sessions.test").one()
            with mock.patch.object(security, "PBKDF2_ITERATIONS", 1000):
                user.password_hash = security.hash_password(PW)
            session.commit()
        self.sign_in("root@sessions.test")
        with get_session_factory()() as session:
            stored = session.query(User).filter_by(email="root@sessions.test").one().password_hash
        self.assertNotEqual(stored.split("$")[1], "1000")


if __name__ == "__main__":
    unittest.main()
