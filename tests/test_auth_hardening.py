"""Sign-in hardening from the production-readiness audit (2026-10-05).

1. An unknown or deactivated email answered faster than a real one with a wrong password
   (it skipped the PBKDF2 work), so response timing told an attacker which emails exist.
2. A token's `typ` was written as "access" but never checked on the way in.
3. A token outlived a password change: whoever held the old one kept the session. Tokens
   now carry a fingerprint of the password hash, checked on every request; a change (or an
   administrator's reset) retires every token issued before it.
4. The current-password check on change-password had no attempt limit.
5. Sign-ins, successful or not, were not in the audit trail.
"""
from __future__ import annotations

import inspect
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jwt  # noqa: E402

from api.auth import dependencies, routes, security, service  # noqa: E402

SECRET = {"PORTAL_AUTH_SECRET": "x" * 64}


class _NoUser:
    def scalar(self, *_a, **_k):
        return None


class LoginTiming(unittest.TestCase):
    def test_an_unknown_email_does_the_same_password_work_as_a_real_one(self):
        with mock.patch.object(security, "verify_password", return_value=False) as verify:
            with self.assertRaises(service.AuthError):
                service.authenticate_user(_NoUser(), "nobody@example.test", "guess")
        self.assertEqual(verify.call_count, 1)   # the dummy check: the same PBKDF2 work


class TokenChecks(unittest.TestCase):
    def test_only_an_access_token_is_accepted(self):
        with mock.patch.dict(os.environ, SECRET):
            other = jwt.encode({"sub": "u1", "typ": "embed", "exp": 9999999999}, security.jwt_secret(), algorithm="HS256")
            with self.assertRaises(jwt.PyJWTError):
                security.decode_access_token(other)
            good = security.create_access_token(user_id="u1", email="a@b.c", role="user", client_id="c",
                                                organization_id="citycorp", workstreams=[], pwv="abc")
            self.assertEqual(security.decode_access_token(good)["sub"], "u1")

    def test_a_password_change_retires_older_tokens(self):
        old_hash, new_hash = security.hash_password("Old-Password-1!"), security.hash_password("New-Password-1!")
        with mock.patch.dict(os.environ, SECRET):
            token = security.create_access_token(user_id="u1", email="a@b.c", role="user", client_id="c",
                                                 organization_id="citycorp", workstreams=[],
                                                 pwv=security.password_fingerprint(old_hash))
            payload = security.decode_access_token(token)
        self.assertTrue(security.token_password_current(payload, old_hash))
        self.assertFalse(security.token_password_current(payload, new_hash))
        self.assertNotIn(old_hash, token)   # the fingerprint is not the hash

    def test_every_request_checks_it(self):
        self.assertIn("token_password_current(", inspect.getsource(dependencies))


class Routes(unittest.TestCase):
    def test_change_password_is_rate_limited(self):
        self.assertIn("check_login_rate_limit(", inspect.getsource(routes.change_password_route))

    def test_sign_ins_are_audited_both_ways(self):
        src = inspect.getsource(routes.login)
        self.assertIn('action="login"', src)
        self.assertIn('action="login_failed"', src)

    def test_every_token_issued_carries_the_fingerprint(self):
        import re
        for path in (ROOT / "api").rglob("*.py"):
            text = path.read_text()
            for m in re.finditer(r"create_access_token\((.*?)\)\n", text, re.S):
                if "def create_access_token" in text[max(0, m.start() - 4):m.start() + 30]:
                    continue
                self.assertIn("pwv=", m.group(1), f"{path.relative_to(ROOT)} issues a token without pwv")


if __name__ == "__main__":
    unittest.main()
