"""GET /portal/letters, /portal/letters/{id}, /portal/letters/{id}/pdf: who may, for which org,
and what is recorded.

letters:read (editor and admin); a row-restricted person is refused (a letter cannot be
filtered by their rules); the org comes only from require_org_for_data; ids are validated
before any read; Postgres and Oracle organizations are served, an org with no connection or
an unreachable database gets a 503, and an engine letters do not read a 501; every response
carries Cache-Control: no-store; every list, preview and PDF is audited with ids and counts,
never a name or an address.
"""
from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import letters_fixtures as fx  # noqa: E402
from api.auth.dependencies import AuthContext, _dev_context, get_auth_context  # noqa: E402
from api.auth.permissions import permissions_for_role  # noqa: E402
from api.letters import repository, routes  # noqa: E402
from api.letters.source import RowCeilingExceeded  # noqa: E402

PII = ("rivera", "alex", "example avenue", "springfield", "62701")


def ctx(org="demo25", role="editor", rules=(), perms=None):
    return AuthContext(id="u1", email="u1@utility.gov", display_name="u1", role=role, client_id="smartcity",
                       organization_id=org, organization_name=org,
                       permissions=set(perms if perms is not None else permissions_for_role(role)),
                       workstreams=["*"], row_rules=tuple(rules))


class RouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(routes.router)
        self.app, self.client = app, TestClient(app)
        self.as_(ctx())
        self.audit = mock.MagicMock()
        letters = fx.every_kind()
        by_id = {l.letter_id: l for l in letters}
        self.patches = [
            mock.patch("api.org_db.warehouse_configured", return_value=True),
            mock.patch("api.org_db.demo_configured", return_value=False),
            mock.patch.object(routes, "warehouse_configured", return_value=True),
            mock.patch.object(routes, "record_access_event", self.audit),
            mock.patch.object(repository, "list_letters", return_value=letters),
            mock.patch.object(repository, "get_letter", side_effect=lambda _org, i: by_id.get(i)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def as_(self, context):
        self.app.dependency_overrides[get_auth_context] = lambda: context

    def get(self, path):
        r = self.client.get(path)
        self.assertEqual(r.headers.get("cache-control"), "no-store", f"{path} -> {r.status_code}")
        return r

    LIST = "/portal/letters?from=2028-03-01&to=2028-03-31"

    # ---- who may ------------------------------------------------------------------
    def test_letters_read_belongs_to_editors_and_admins(self):
        self.assertNotIn("letters:read", permissions_for_role("user"))
        self.assertIn("letters:read", permissions_for_role("editor"))
        self.assertIn("letters:read", permissions_for_role("admin"))
        self.assertIn("letters:read", _dev_context().permissions, "the sign-in-off developer is an admin")

    def test_403_without_the_permission(self):
        self.as_(ctx(role="user"))
        for path in (self.LIST, "/portal/letters/CC-3000000001", "/portal/letters/CC-3000000001/pdf"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 403)
        self.audit.assert_not_called()

    def test_403_for_a_row_restricted_person(self):
        self.as_(ctx(rules=({"field": "Service Type", "values": ["Water"]},)))
        for path in (self.LIST, "/portal/letters/CC-3000000001", "/portal/letters/CC-3000000001/pdf"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 403)
        repository.list_letters.assert_not_called()

    def test_the_org_comes_only_from_require_org_for_data(self):
        src = inspect.getsource(routes)
        self.assertIn("require_org_for_data(ctx)", src)
        self.assertNotIn("ctx.organization_id", src)
        self.get(self.LIST + "&organization_id=ellensburg")
        self.assertEqual(repository.list_letters.call_args.args[0], "demo25")

    # ---- which org ----------------------------------------------------------------
    def test_503_when_the_org_has_no_data_source(self):
        with mock.patch("api.org_db.warehouse_configured", return_value=False):
            self.assertEqual(self.get(self.LIST).status_code, 503)
        with mock.patch.object(routes, "warehouse_configured", return_value=False):
            self.assertEqual(self.get("/portal/letters/CC-3000000001/pdf").status_code, 503)
        repository.list_letters.assert_not_called()

    def oracle_org(self, *, connected=True):
        """Ellensburg as the portal sees it: an Oracle org with its own connection and no warehouse."""
        self.as_(ctx(org="ellensburg"))
        for p in (mock.patch("api.org_db.warehouse_configured", return_value=False),
                  mock.patch("api.org_db.demo_configured", return_value=connected),
                  mock.patch.object(routes, "warehouse_configured", return_value=False),
                  mock.patch.object(routes, "demo_configured", return_value=connected)):
            p.start()
            self.addCleanup(p.stop)

    def test_an_oracle_org_is_served(self):
        self.oracle_org()
        for path in (self.LIST, "/portal/letters/CC-3000000001", "/portal/letters/CC-3000000001/pdf"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 200)
        self.assertEqual(repository.list_letters.call_args.args[0], "ellensburg")
        self.assertEqual(repository.get_letter.call_args.args[0], "ellensburg")

    def test_503_when_an_oracle_org_has_no_connection(self):
        self.oracle_org(connected=False)
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 503)
        with mock.patch("api.org_db.warehouse_configured", return_value=True):   # past the org check
            r = self.get("/portal/letters/CC-3000000001/pdf")
        self.assertEqual(r.status_code, 503)
        self.assertIn("none is configured", r.json()["detail"])
        repository.list_letters.assert_not_called()
        repository.get_letter.assert_not_called()

    def test_503_when_the_database_cannot_be_reached(self):
        self.oracle_org()
        repository.list_letters.side_effect = RuntimeError(
            "DPY-6005: cannot connect to database (CONNECTION_ID=x). ORA-12170 host=db.example.internal")
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 503)
        self.assertIn("cannot be reached", r.json()["detail"])
        self.assertNotIn("example.internal", r.text)

    def test_504_when_the_read_times_out(self):
        # Ellensburg 2026-09-29: the balances query passed its 120 s limit while the warehouse
        # rebuilt, and the page said only "could not be read"
        self.oracle_org()
        repository.list_letters.side_effect = RuntimeError(
            "DPY-4024: call timeout of 120000 ms exceeded\nORA-03156: OCI call timed out")
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 504)
        self.assertIn("took too long", r.json()["detail"])

    def test_501_for_an_engine_letters_do_not_read(self):
        with mock.patch.object(routes, "org_backend", return_value=("snowflake", "dbt")):
            r = self.get(self.LIST)
        self.assertEqual(r.status_code, 501)
        self.assertIn("not available for this organization yet", r.json()["detail"])
        repository.list_letters.assert_not_called()

    # ---- what is asked ------------------------------------------------------------
    def test_422_for_a_malformed_letter_id(self):
        for bad in ("CC-12AB", "XX-123", "CC-", "CC-123456789012345", "cc-123", "CC-1%20or%201=1"):
            for tail in ("", "/pdf"):
                with self.subTest(id=bad, tail=tail):
                    self.assertEqual(self.get(f"/portal/letters/{bad}{tail}").status_code, 422)
        repository.get_letter.assert_not_called()

    def test_422_for_a_bad_window(self):
        for query in ("", "?from=2028-03-01", "?from=2028-13-01&to=2028-03-31", "?from=2028-03-31&to=2028-03-01",
                      "?from=2026-01-01&to=2028-03-31"):
            with self.subTest(query=query):
                self.assertEqual(self.get(f"/portal/letters{query}").status_code, 422)
        repository.list_letters.assert_not_called()

    def test_404_for_an_unknown_letter(self):
        self.assertEqual(self.get("/portal/letters/CC-9999999999").status_code, 404)
        self.assertEqual(self.get("/portal/letters/ADJ-999999999999/pdf").status_code, 404)

    def test_a_window_past_the_row_ceiling_asks_for_a_shorter_one(self):
        repository.list_letters.side_effect = RowCeilingExceeded("collection_events", 100000)
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 422)
        self.assertIn("shorter", r.json()["detail"])

    def test_a_database_failure_is_a_502_that_leaks_nothing(self):
        repository.list_letters.side_effect = RuntimeError("connection to host=db user=portal password=hunter2 failed")
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("hunter2", r.text)

    # ---- what is served and recorded ----------------------------------------------
    def test_the_page_opens_on_the_month_before_the_data_ends(self):
        # a frozen copy (Ellensburg, as of 2026-06-18) opens on May 2026, not the viewer's last month
        with mock.patch.object(routes, "data_as_of", return_value="2026-06-18"):
            r = self.get("/portal/letters/as-of")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"data_as_of": "2026-06-18"})
        with mock.patch.object(routes, "data_as_of", return_value=None):
            self.assertEqual(self.get("/portal/letters/as-of").json(), {"data_as_of": None})

    def test_the_list(self):
        r = self.get(self.LIST)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual((body["organization_id"], body["count"]), ("demo25", len(fx.every_kind())))
        first = body["letters"][0]
        self.assertEqual(first["letter_id"], "CC-3000000001")
        self.assertEqual((first["kind"], first["kind_label"]), ("reminder", "Past due reminder"))
        self.assertEqual(repository.list_letters.call_args.args[0], "demo25")

    def test_one_letter_with_its_words_and_the_process_behind_it(self):
        r = self.get("/portal/letters/CC-3000000002")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["letter"]["letter_id"], "CC-3000000002")
        self.assertEqual(body["composed"]["subject"], "NOTICE OF DISCONNECTION FOR NON-PAYMENT")
        self.assertEqual(body["process"]["process_id"], "4000000002")
        self.assertEqual(body["recipient"]["address_lines"][0], "Rivera,Alex")

    def test_the_pdf(self):
        r = self.get("/portal/letters/ADJ-600000000002/pdf")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF-"))
        self.assertIn("inline", r.headers["content-disposition"])
        self.assertIn(r.headers["x-letter-font"], ("DejaVu Sans", "Helvetica"))

    def test_every_list_preview_and_pdf_is_audited_with_ids_and_counts_only(self):
        self.get(self.LIST)
        self.get("/portal/letters/CC-3000000001")
        self.get("/portal/letters/CC-3000000001/pdf")
        calls = [c.kwargs for c in self.audit.call_args_list]
        self.assertEqual([c["action"] for c in calls], ["letters_list", "letter_preview", "letter_pdf"])
        self.assertIn(f"letters={len(fx.every_kind())}", calls[0]["detail"])
        self.assertEqual(calls[1]["target_id"], "CC-3000000001")
        self.assertIn("pages=1", calls[2]["detail"])
        for c in calls:
            self.assertEqual(c["actor_email"], "u1@utility.gov")
            recorded = " ".join(str(v) for v in c.values()).lower()
            for pii in PII:
                self.assertNotIn(pii, recorded)



class BrowserReadsTheFontHeadersTests(unittest.TestCase):
    """The portal runs on another origin, so a browser hides every response header the CORS
    policy does not expose: without this the preview could never say its font was substituted."""

    def test_the_pdf_exposes_its_font_headers_and_the_request_id(self):
        from api.app import app
        letters = {l.letter_id: l for l in fx.every_kind()}
        patches = [
            mock.patch("api.org_db.warehouse_configured", return_value=True),
            mock.patch("api.org_db.demo_configured", return_value=False),
            mock.patch.object(routes, "warehouse_configured", return_value=True),
            mock.patch.object(routes, "record_access_event"),
            mock.patch.object(repository, "get_letter", side_effect=lambda _org, i: letters.get(i)),
            mock.patch.object(routes.render, "resolve_font",
                              return_value=routes.render.Font("Helvetica", "Helvetica-Bold", "Helvetica", "substituted")),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        app.dependency_overrides[get_auth_context] = lambda: ctx()
        self.addCleanup(app.dependency_overrides.pop, get_auth_context, None)

        r = TestClient(app).get("/portal/letters/ADJ-600000000002/pdf", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["x-letter-font-note"], "substituted")
        exposed = {h.strip().lower() for h in r.headers["access-control-expose-headers"].split(",")}
        self.assertTrue({"x-request-id", "x-letter-font", "x-letter-font-note"} <= exposed, exposed)


if __name__ == "__main__":
    unittest.main()
