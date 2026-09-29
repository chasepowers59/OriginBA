"""Letter runs: a frozen list of letters, approved by a second person, released as one print file.

POST /portal/letters/runs freezes the window's letters into a manifest (ids and fingerprints of
what each letter says, never the words themselves); approve moves draft -> approved and is refused
to the run's creator; release re-reads every letter, refuses when any changed or disappeared, and
answers one merged PDF from memory; cancel ends a draft or approved run. Every route is no-store,
every step is audited with ids and counts only, and the store keeps 200 runs per organization
without ever dropping one that is still open.
"""
from __future__ import annotations

import base64
import builtins
import dataclasses
import json
import re
import sys
import tempfile
import unittest
import zlib
from datetime import datetime
from decimal import Decimal
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
from api.letters import repository, routes, runs  # noqa: E402
from api.letters.catalog import catalog  # noqa: E402
from api.letters.model import Kind  # noqa: E402

PII = ("rivera", "alex", "example avenue", "springfield", "62701")
AMOUNTS = ("132.69", "187.45", "84.87", "212.40", "598.45", "10.88")
RUNS = "/portal/letters/runs"
WINDOW = {"from": "2028-03-01", "to": "2028-03-31"}
RUN_PERMISSIONS = ("letters:generate", "letters:approve", "letters:release")


def ctx(uid="u1", org="demo25", role="editor", rules=(), perms=None):
    return AuthContext(id=uid, email=f"{uid}@utility.gov", display_name=uid, role=role, client_id="smartcity",
                       organization_id=org, organization_name=org,
                       permissions=set(perms if perms is not None else permissions_for_role(role)),
                       workstreams=["*"], row_rules=tuple(rules))


def unique_letters():
    """One of every kind, each with its own id (every_kind repeats the reminder's)."""
    return [dataclasses.replace(l, letter_id=f"{l.letter_id.split('-')[0]}-{n + 1:04d}")
            for n, l in enumerate(fx.every_kind())]


def page_refs(pdf: bytes) -> list[str]:
    """The letter id printed on each page's stub, in page order (reportlab: ASCII85 + Flate)."""
    ids = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", pdf, re.S):
        raw = m.group(1).strip().removesuffix(b"~>")
        ids += [i.decode() for i in re.findall(rb"\(Ref ((?:CC|ADJ)-\d+)", zlib.decompress(base64.a85decode(raw)))]
    return ids


def page_count(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf))


class RunRoutesBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store_path = Path(self.tmp.name) / "letter_runs.json"
        app = FastAPI()
        app.include_router(routes.router)
        self.app, self.client = app, TestClient(app)
        self.as_(ctx())
        self.audit = mock.MagicMock()
        self.letters = unique_letters()
        self.patches = [
            mock.patch.object(runs, "RUNS_PATH", self.store_path),
            mock.patch("api.portal_state_store.enabled", return_value=False),
            mock.patch("api.org_db.warehouse_configured", return_value=True),
            mock.patch("api.org_db.demo_configured", return_value=False),
            mock.patch.object(routes, "warehouse_configured", return_value=True),
            mock.patch.object(routes, "record_access_event", self.audit),
            mock.patch.object(repository, "list_letters", side_effect=lambda *_a, **_k: list(self.letters)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def as_(self, context):
        self.app.dependency_overrides[get_auth_context] = lambda: context

    def call(self, method, path, **kw):
        r = self.client.request(method, path, **kw)
        self.assertEqual(r.headers.get("cache-control"), "no-store", f"{method} {path} -> {r.status_code}")
        return r

    def create(self, **body):
        r = self.call("POST", RUNS, json={**WINDOW, **body})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def approve(self, run_id, uid="u2"):
        self.as_(ctx(uid))
        return self.call("POST", f"{RUNS}/{run_id}/approve")

    def release(self, run_id, uid="u1"):
        self.as_(ctx(uid))
        return self.call("POST", f"{RUNS}/{run_id}/release")

    def approved(self):
        """Created by u1, approved by u2."""
        self.as_(ctx("u1"))
        run = self.create()
        self.assertEqual(self.approve(run["id"]).status_code, 200)
        return run


class StateMachineTests(RunRoutesBase):
    def test_a_run_freezes_the_window_as_a_draft_with_counts_by_type(self):
        run = self.create()
        self.assertEqual(run["status"], "draft")
        self.assertEqual((run["from"], run["to"]), ("2028-03-01", "2028-03-31"))
        self.assertEqual(run["counts"]["letters"], len(self.letters))
        by_kind = {k["kind"]: k["count"] for k in run["counts"]["by_kind"]}
        self.assertEqual(by_kind["reminder"], 1)
        self.assertEqual(sum(by_kind.values()), len(self.letters))
        self.assertEqual(run["created_by"], "u1@utility.gov")
        self.assertTrue(run["created_by_you"])
        self.assertEqual([h["status"] for h in run["history"]], ["draft"])
        self.assertNotIn("manifest", run)

    def test_filters_choose_the_letters_by_type_and_status(self):
        run = self.create(filters={"kinds": ["reminder", "late_fee"], "printed": "not_printed"})
        self.assertEqual(run["counts"]["letters"], 2)
        self.assertEqual(run["filters"], {"kinds": ["reminder", "late_fee"], "printed": "not_printed"})

    def test_a_filter_the_server_does_not_know_is_refused(self):
        for filters in ({"search": "rivera"}, {"kinds": ["nope"]}, {"printed": "sometimes"}):
            with self.subTest(filters=filters):
                self.assertEqual(self.call("POST", RUNS, json={**WINDOW, "filters": filters}).status_code, 422)

    def test_an_empty_or_a_bad_window_is_refused(self):
        self.letters = []
        r = self.call("POST", RUNS, json=WINDOW)
        self.assertEqual(r.status_code, 422)
        self.assertIn("No letters", r.json()["detail"])
        for body in ({"from": "2028-03-31", "to": "2028-03-01"}, {"from": "2026-01-01", "to": "2028-03-31"}, {}):
            with self.subTest(body=body):
                self.assertEqual(self.call("POST", RUNS, json=body).status_code, 422)

    def test_a_run_larger_than_one_print_file_may_hold_is_refused(self):
        with mock.patch.object(runs, "MAX_RUN_LETTERS", 3):
            r = self.call("POST", RUNS, json=WINDOW)
        self.assertEqual(r.status_code, 422)
        self.assertIn("at most 3", r.json()["detail"])

    def test_draft_approved_released(self):
        run = self.create()
        r = self.approve(run["id"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["status"], r.json()["approved_by"]), ("approved", "u2@utility.gov"))
        r = self.release(run["id"])
        self.assertEqual(r.status_code, 200, r.text)
        self.as_(ctx("u3"))
        got = self.call("GET", f"{RUNS}/{run['id']}").json()
        self.assertEqual(got["status"], "released")
        self.assertEqual((got["released_by"], got["pages"]), ("u1@utility.gov", len(self.letters)))
        self.assertEqual([h["status"] for h in got["history"]], ["draft", "approved", "released"])
        self.assertEqual(got["letter_ids"], [l.letter_id for l in self.letters])

    def test_illegal_transitions_are_409(self):
        draft = self.create()
        self.assertEqual(self.release(draft["id"], uid="u3").status_code, 409, "a draft is not released")
        run = self.approved()
        self.assertEqual(self.approve(run["id"], uid="u3").status_code, 409, "approved twice")
        self.assertEqual(self.release(run["id"]).status_code, 200)
        self.as_(ctx("u1"))
        self.assertEqual(self.call("POST", f"{RUNS}/{run['id']}/cancel").status_code, 409, "a released run stays")
        self.assertEqual(self.approve(run["id"], uid="u3").status_code, 409)
        self.as_(ctx("u1"))
        self.assertEqual(self.call("POST", f"{RUNS}/{draft['id']}/cancel").status_code, 200)
        for step in ("approve", "release", "cancel"):
            with self.subTest(step=step):
                self.as_(ctx("u3", role="admin"))
                self.assertEqual(self.call("POST", f"{RUNS}/{draft['id']}/{step}").status_code, 409)

    def test_a_released_run_downloads_again_but_stays_released(self):
        run = self.approved()
        first = self.release(run["id"]).content
        again = self.release(run["id"], uid="u3")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(page_refs(again.content), page_refs(first))
        got = self.call("GET", f"{RUNS}/{run['id']}").json()
        self.assertEqual(got["released_by"], "u1@utility.gov", "the first release is the one recorded")
        self.assertEqual([h["status"] for h in got["history"]], ["draft", "approved", "released"])

    def test_cancel_by_the_creator_or_an_admin_only(self):
        run = self.create()
        self.as_(ctx("u2"))
        r = self.call("POST", f"{RUNS}/{run['id']}/cancel")
        self.assertEqual(r.status_code, 403)
        self.assertIn("created", r.json()["detail"])
        self.as_(ctx("u3", role="admin"))
        r = self.call("POST", f"{RUNS}/{run['id']}/cancel")
        self.assertEqual((r.status_code, r.json()["status"]), (200, "cancelled"))
        approved = self.approved()
        self.as_(ctx("u1"))
        self.assertEqual(self.call("POST", f"{RUNS}/{approved['id']}/cancel").json()["status"], "cancelled")

    def test_runs_are_listed_newest_first_without_their_manifests(self):
        ids = [self.create()["id"] for _ in range(3)]
        body = self.call("GET", RUNS).json()
        self.assertEqual([r["id"] for r in body["runs"]], ids[::-1])
        self.assertTrue(all("manifest" not in r and "letter_ids" not in r for r in body["runs"]))

    def test_an_unknown_or_malformed_run_id(self):
        self.assertEqual(self.call("GET", f"{RUNS}/0123456789abcdef0123456789abcdef").status_code, 404)
        for bad in ("nope", "0123456789abcdef0123456789abcdeg", "0123456789ABCDEF0123456789ABCDEF"):
            with self.subTest(id=bad):
                self.assertEqual(self.call("POST", f"{RUNS}/{bad}/approve").status_code, 422)

    def test_one_org_never_sees_anothers_run(self):
        run = self.create()
        self.as_(ctx("u2", org="odessa"))
        with mock.patch.object(routes, "org_backend", return_value=("postgres", "dbt")):
            self.assertEqual(self.call("GET", f"{RUNS}/{run['id']}").status_code, 404)
            self.assertEqual(self.call("POST", f"{RUNS}/{run['id']}/approve").status_code, 404)
            self.assertEqual(self.call("GET", RUNS).json()["runs"], [])


class FourEyesAndPermissionTests(RunRoutesBase):
    def test_the_creator_cannot_approve_their_own_run(self):
        run = self.create()
        for role in ("editor", "admin"):
            with self.subTest(role=role):
                self.as_(ctx("u1", role=role))
                r = self.call("POST", f"{RUNS}/{run['id']}/approve")
                self.assertEqual(r.status_code, 403)
                self.assertIn("someone else", r.json()["detail"])
        self.as_(ctx("u1"))
        self.assertEqual(self.call("GET", f"{RUNS}/{run['id']}").json()["status"], "draft")

    def test_the_same_person_under_another_id_is_still_the_creator(self):
        run = self.create()
        self.as_(AuthContext(id="other-id", email="U1@Utility.gov", display_name="u1", role="editor",
                             client_id="smartcity", organization_id="demo25", organization_name="demo25",
                             permissions=permissions_for_role("editor"), workstreams=["*"]))
        self.assertEqual(self.call("POST", f"{RUNS}/{run['id']}/approve").status_code, 403)

    def test_the_role_map(self):
        for perm in RUN_PERMISSIONS:
            with self.subTest(perm=perm):
                self.assertNotIn(perm, permissions_for_role("user"))
                self.assertIn(perm, permissions_for_role("editor"))
                self.assertIn(perm, permissions_for_role("admin"))
                self.assertIn(perm, _dev_context().permissions)

    def test_each_step_needs_its_permission(self):
        run = self.create()
        steps = {"letters:read": [("GET", RUNS), ("GET", f"{RUNS}/{run['id']}")],
                 "letters:generate": [("POST", RUNS), ("POST", f"{RUNS}/{run['id']}/cancel")],
                 "letters:approve": [("POST", f"{RUNS}/{run['id']}/approve")],
                 "letters:release": [("POST", f"{RUNS}/{run['id']}/release")]}
        everything = set(permissions_for_role("admin"))
        for perm, calls in steps.items():
            for method, path in calls:
                with self.subTest(perm=perm, path=path):
                    self.as_(ctx("u2", perms=everything - {perm}))
                    self.assertEqual(self.call(method, path, json=WINDOW).status_code, 403)
        self.as_(ctx("u2", role="user"))
        self.assertEqual(self.call("GET", RUNS).status_code, 403)

    def test_a_row_restricted_person_is_refused_everywhere(self):
        run = self.create()
        self.as_(ctx("u2", rules=({"field": "Service Type", "values": ["Water"]},)))
        for method, path in (("GET", RUNS), ("POST", RUNS), ("GET", f"{RUNS}/{run['id']}"),
                             ("POST", f"{RUNS}/{run['id']}/approve"), ("POST", f"{RUNS}/{run['id']}/release"),
                             ("POST", f"{RUNS}/{run['id']}/cancel")):
            with self.subTest(path=path, method=method):
                self.assertEqual(self.call(method, path, json=WINDOW).status_code, 403)


class ReleaseTests(RunRoutesBase):
    def test_one_merged_pdf_one_page_per_letter_in_manifest_order(self):
        self.letters = self.letters[::-1]            # the manifest keeps the order it was read in
        run = self.approved()
        self.letters = sorted(self.letters, key=lambda l: l.letter_id)   # CISADM answers in another order
        r = self.release(run["id"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertIn("attachment", r.headers["content-disposition"])
        self.assertEqual(page_count(r.content), len(self.letters))
        self.assertEqual(page_refs(r.content), [l.letter_id for l in unique_letters()[::-1]])

    def test_a_changed_letter_blocks_the_release(self):
        run = self.approved()
        l = self.letters[0]
        self.letters[0] = dataclasses.replace(l, account_balance=l.account_balance + Decimal("1.00"))
        r = self.release(run["id"])
        self.assertEqual(r.status_code, 409)
        self.assertIn("1 letter changed", r.json()["detail"])
        self.assertIn("new run", r.json()["detail"])
        self.assertEqual(self.call("GET", f"{RUNS}/{run['id']}").json()["status"], "approved")

    def test_a_changed_address_blocks_the_release(self):
        run = self.approved()
        l = self.letters[1]
        self.letters[1] = dataclasses.replace(
            l, mailing_address=dataclasses.replace(l.mailing_address, address1="200 Other Street"))
        self.assertEqual(self.release(run["id"]).status_code, 409)

    def test_a_letter_that_disappeared_blocks_the_release(self):
        run = self.approved()
        del self.letters[2]
        r = self.release(run["id"])
        self.assertEqual(r.status_code, 409)
        self.assertIn("1 letter no longer exists", r.json()["detail"])

    def test_a_released_run_that_changed_is_not_downloaded_again(self):
        run = self.approved()
        self.assertEqual(self.release(run["id"]).status_code, 200)
        del self.letters[0]
        self.assertEqual(self.release(run["id"]).status_code, 409)

    def test_the_print_stamp_c2m_adds_later_is_not_a_change(self):
        run = self.approved()
        self.letters = [dataclasses.replace(l, printed_at=datetime(2028, 4, 1)) for l in self.letters]
        self.assertEqual(self.release(run["id"]).status_code, 200)

    def test_nothing_but_the_run_record_is_written_to_disk(self):
        run = self.approved()
        written: list[str] = []
        real_open = builtins.open

        def spy(file, mode="r", *a, **k):
            if isinstance(file, (str, Path)) and any(c in mode for c in "wax+"):
                written.append(str(file))
            return real_open(file, mode, *a, **k)

        with mock.patch("builtins.open", spy), mock.patch("io.open", spy), \
                mock.patch("tempfile.NamedTemporaryFile") as ntf, mock.patch("tempfile.mkstemp") as mkstemp:
            r = self.release(run["id"])
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.content.startswith(b"%PDF-"))
        self.assertEqual(set(written), {str(self.store_path)})
        ntf.assert_not_called()
        mkstemp.assert_not_called()
        self.assertNotIn(b"%PDF", self.store_path.read_bytes())


class StoredAndAuditedTests(RunRoutesBase):
    def full_cycle(self):
        run = self.approved()
        self.release(run["id"])
        self.release(run["id"], uid="u3")
        self.as_(ctx("u1"))
        other = self.create()
        self.call("POST", f"{RUNS}/{other['id']}/cancel")
        del self.letters[0]
        self.release(run["id"])
        return run

    def test_every_step_is_audited_with_ids_and_counts_only(self):
        run = self.full_cycle()
        calls = [c.kwargs for c in self.audit.call_args_list]
        self.assertEqual([c["action"] for c in calls],
                         ["letter_run_create", "letter_run_approve", "letter_run_release", "letter_run_download",
                          "letter_run_create", "letter_run_cancel", "letter_run_release_refused"])
        self.assertEqual(calls[0]["target_type"], "letter_run")
        self.assertEqual(calls[0]["target_id"], run["id"])
        self.assertIn(f"letters={len(unique_letters())}", calls[0]["detail"])
        self.assertIn(f"pages={len(unique_letters())}", calls[2]["detail"])
        self.assertIn("missing=1", calls[-1]["detail"])
        for c in calls:
            recorded = " ".join(str(v) for v in c.values()).lower()
            for secret in PII + AMOUNTS:
                self.assertNotIn(secret, recorded)

    def test_the_stored_run_holds_ids_and_fingerprints_only(self):
        self.full_cycle()
        stored = self.store_path.read_text(encoding="utf-8").lower()
        for secret in PII + AMOUNTS:
            self.assertNotIn(secret, stored)
        record = json.loads(stored)["runs"][0]
        self.assertEqual({len(m) for m in record["manifest"]}, {2})

    def test_fingerprints_track_what_the_letter_says(self):
        words, name = catalog().words("demo25"), "Test Utility"
        l = fx.reminder()
        fp = runs.fingerprint(l, words, name)
        self.assertEqual(fp, runs.fingerprint(dataclasses.replace(l), words, name))
        self.assertEqual(fp, runs.fingerprint(dataclasses.replace(l, printed_at=l.created_at), words, name))
        changed = (dataclasses.replace(l, account_balance=Decimal("1")),
                   dataclasses.replace(l, customer_name="Someone,Else"),
                   dataclasses.replace(l, debt=dataclasses.replace(l.debt, next_action_on=None)),
                   dataclasses.replace(l, kind=Kind.DEPOSIT))
        for other in changed:
            self.assertNotEqual(fp, runs.fingerprint(other, words, name))
        self.assertNotEqual(fp, runs.fingerprint(l, dataclasses.replace(words, contact_phone="555"), name))


class RetentionTests(RunRoutesBase):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(runs, "MAX_RUNS", 3)
        p.start()
        self.addCleanup(p.stop)

    def test_past_the_cap_of_open_runs_a_new_draft_is_refused_and_none_is_lost(self):
        ids = [self.create()["id"] for _ in range(3)]
        r = self.call("POST", RUNS, json=WINDOW)
        self.assertEqual(r.status_code, 409)
        self.assertIn("limit of 3", r.json()["detail"])
        self.assertEqual(sorted(x["id"] for x in self.call("GET", RUNS).json()["runs"]), sorted(ids))

    def test_the_oldest_finished_run_makes_room(self):
        released = self.approved()
        self.release(released["id"])
        self.as_(ctx("u1"))
        drafts = [self.create()["id"] for _ in range(2)]
        newest = self.create()["id"]
        kept = [x["id"] for x in self.call("GET", RUNS).json()["runs"]]
        self.assertEqual(kept, [newest, *drafts[::-1]])


class NoStoreTests(RunRoutesBase):
    def test_every_run_route_is_no_store_including_refusals(self):
        run = self.create()
        for uid in ("u1", "u2"):                     # the creator is refused approve; the other allowed
            self.as_(ctx(uid))
            for method, path in (("GET", RUNS), ("GET", f"{RUNS}/{run['id']}"), ("POST", f"{RUNS}/{run['id']}/approve"),
                                 ("POST", f"{RUNS}/{run['id']}/release"), ("POST", f"{RUNS}/{run['id']}/cancel"),
                                 ("GET", f"{RUNS}/nope")):
                with self.subTest(uid=uid, path=path):
                    self.call(method, path)            # call() asserts the header


if __name__ == "__main__":
    unittest.main()
