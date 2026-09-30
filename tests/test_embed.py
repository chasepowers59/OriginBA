"""Embedding a saved view in another site with a signed, expiring link.

POST /portal/embed-tokens {view_id, ttl_minutes} (the view's owner or an admin) returns a
token signed with the portal secret: the organization, the view, the creator's row rules
and an expiry of at most 24 hours. GET /embed/{token}/data runs that one view's definition
through the query builder with those rules and returns its rows, and nothing else: an
expired, tampered or wrong-purpose token is refused, and no other canvas or view is
reachable with it. A private view cannot be embedded.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import jwt
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import embed  # noqa: E402
from api import portal_routes as pr  # noqa: E402
from api import saved_views as sv  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402

SECRET = "test-secret-at-least-thirty-two-characters-long"
PERMS = {"portal:read", "saved_views:write"}


def _user(uid, role="editor", rules=()):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id="dev",
                       organization_id="dev", organization_name="Dev", permissions=set(PERMS), workstreams=["*"],
                       row_rules=tuple(rules))


class EmbedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.executed = []

        def run(sql, binds=None, **_):
            self.executed.append((sql, binds))
            return ["Bill Cycle", "m0"], [["C1", 12.5]]
        self.patches = [
            mock.patch.dict(os.environ, {"PORTAL_AUTH_SECRET": SECRET}),
            mock.patch.object(sv, "VIEWS_PATH", Path(self.tmp.name) / "v.json"),
            mock.patch.object(sv._pss, "enabled", return_value=False),
            mock.patch("api.snapshot_catalog.snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch("api.warehouse_db.execute_query", side_effect=run),
            mock.patch("api.access_audit.record_access_event"),
            # sign-in switched off: embeds use the rules stored in the token (creator_rules)
            mock.patch("api.row_security.auth_disabled", return_value=True),
        ]
        for p in self.patches:
            p.start()
        self.alice = _user("alice", rules=({"field": "Service Type", "values": ["Water"]},))
        self.view = pr.post_saved_view(pr.SavedViewCreate(
            snapshot_id="rpt_bill_segment", snapshot_label="Bill Segment", title="Billed by cycle", kind="custom",
            dimensions=["Bill Cycle"], measures=[{"field": "Billed Amount", "agg": "sum"}],
            filters=[{"field": "Is Frozen", "op": "eq", "value": True}]), ctx=self.alice)

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def _token(self, ctx=None, view_id=None, ttl=60):
        return embed.create_embed_token(embed.EmbedTokenRequest(view_id=view_id or self.view["id"], ttl_minutes=ttl),
                                        ctx=ctx or self.alice)["token"]

    def test_an_embedded_view_returns_its_rows_with_the_creators_rules(self):
        out = embed.embed_data(self._token())
        self.assertEqual(out["title"], "Billed by cycle")
        # measures carry their names, as in the builder, never the SQL alias m0
        self.assertEqual(out["rows"], [{"Bill Cycle": "C1", "Total Billed Amount": 12.5}])
        sql, binds = self.executed[-1]
        self.assertIn('"Is Frozen"', sql)
        self.assertIn('"Service Type" IN', sql)

    def test_only_the_owner_or_an_admin_embeds_a_view(self):
        with self.assertRaises(HTTPException) as err:
            self._token(ctx=_user("bob"))
        self.assertEqual(err.exception.status_code, 403)
        self.assertTrue(self._token(ctx=_user("root", role="admin")))

    def test_a_private_view_cannot_be_embedded(self):
        private = pr.post_saved_view(pr.SavedViewCreate(snapshot_id="rpt_bill_segment", snapshot_label="Bill Segment",
                                                        title="mine", kind="custom", visibility="private"), ctx=self.alice)
        with self.assertRaises(HTTPException) as err:
            self._token(view_id=private["id"])
        self.assertEqual(err.exception.status_code, 400)

    def test_the_lifetime_is_capped_at_a_day(self):
        token = self._token(ttl=60 * 24 * 30)
        exp = jwt.decode(token, SECRET, algorithms=["HS256"])["exp"]
        self.assertLessEqual(exp - time.time(), 24 * 3600 + 5)

    def test_expired_tampered_or_foreign_tokens_are_refused(self):
        good = jwt.decode(self._token(), SECRET, algorithms=["HS256"])
        bad = [jwt.encode({**good, "exp": int(time.time()) - 5}, SECRET, algorithm="HS256"),
               jwt.encode(good, "another-secret-another-secret-another-secret", algorithm="HS256"),
               jwt.encode({**good, "purpose": "access"}, SECRET, algorithm="HS256"),
               "not-a-token"]
        for token in bad:
            with self.assertRaises(HTTPException) as err:
                embed.embed_data(token)
            self.assertEqual(err.exception.status_code, 401)

    def test_a_deleted_view_stops_serving(self):
        token = self._token()
        sv.delete_saved_view(self.view["id"], organization_id="dev")
        with self.assertRaises(HTTPException) as err:
            embed.embed_data(token)
        self.assertEqual(err.exception.status_code, 404)

    def test_a_deactivated_creators_embeds_stop(self):
        token = self._token()
        with mock.patch("api.row_security.auth_disabled", return_value=False), \
             mock.patch("api.row_security._user_record", return_value={"is_active": False, "role": "editor", "row_rules": []}):
            with self.assertRaises(HTTPException) as err:
                embed.embed_data(token)
        self.assertEqual(err.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
