"""The analytics assistant (api/assistant.py): what it may reach and how the loop behaves.

Everything runs without a key or a network: a fake model client scripts the tool calls, the
warehouse executor is patched, and the catalog is the real one. What is asserted is the part
that must hold regardless of what the model says: the canvases-only fence, the validated path,
the row cap, the audit, the loop cap, and the routes' answers when the feature is not set up.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ENVIRONMENT", "test")

from api.assistant import (  # noqa: E402
    MAX_ROWS, MAX_TURNS, Assistant, enforce_canvases_only, tool_describe_canvas,
    tool_list_canvases, tool_search_knowledge,
)
from api.sql_workspace_validator import SqlWorkspaceValidationError  # noqa: E402


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _tool(i, name, inp):
    return SimpleNamespace(type="tool_use", id=i, name=name, input=inp)


def _resp(blocks, stop):
    return SimpleNamespace(content=blocks, stop_reason=stop,
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


class FakeClient:
    """Returns the scripted responses in order; records every request it was given."""
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []
        self.messages = self

    def create(self, **kw):
        self.requests.append(copy.deepcopy(kw))   # a snapshot: the loop mutates its message list
        if not self._responses:
            raise AssertionError("the fake model was asked for more responses than scripted")
        r = self._responses.pop(0)
        return r() if callable(r) else r


class CanvasesOnlyFence(unittest.TestCase):
    def test_reporting_canvases_pass(self):
        for sql in ('select "Billed Amount" from reporting.rpt_bill_segment limit 5',
                    'SELECT 1 FROM ORIGINBA_REPORTING.rpt_gl FETCH FIRST 5 ROWS ONLY',
                    'select * from rpt_payment p join reporting.rpt_customer_account a on 1=1'):
            enforce_canvases_only(sql)

    def test_anything_else_is_refused(self):
        for sql in ('select * from cisadm.ci_acct',
                    'select * from reporting.rpt_bill b join cisadm.ci_bill c on 1=1',
                    'select * from reporting.dim_account',
                    'select * from rpt_bill where 1=(select 1 from cisadm.ci_pay_tndr)',
                    'select 1 from information_schema.tables'):
            with self.assertRaises(SqlWorkspaceValidationError, msg=sql):
                enforce_canvases_only(sql)

    def test_a_comment_cannot_hide_a_table(self):
        with self.assertRaises(SqlWorkspaceValidationError):
            enforce_canvases_only('select 1 from /* reporting.rpt_x */ cisadm.ci_acct')


class Tools(unittest.TestCase):
    def test_canvases_come_from_the_catalog_with_the_engine_s_table_name(self):
        with mock.patch("api.assistant.org_backend", return_value=("postgres", "dbt")):
            c = tool_list_canvases("dev", "postgres")
        self.assertTrue(any(x["id"] == "rpt_bill_segment" for x in c))
        seg = next(x for x in c if x["id"] == "rpt_bill_segment")
        self.assertEqual(seg["table"], "reporting.rpt_bill_segment")
        self.assertEqual(tool_describe_canvas("dev", "oracle_dbt", "rpt_bill_segment")["table"],
                         "ORIGINBA_REPORTING.rpt_bill_segment")

    def test_describe_names_every_column_with_its_meaning(self):
        d = tool_describe_canvas("dev", "postgres", "rpt_bill_segment")
        names = {c["name"] for c in d["columns"]}
        self.assertIn("Billed Amount", names)
        self.assertTrue(all(c["type"] for c in d["columns"]))
        self.assertIn("error", tool_describe_canvas("dev", "postgres", "rpt_nope"))

    def test_knowledge_search_finds_the_frozen_rule(self):
        hits = tool_search_knowledge("dev", "frozen financial transaction money")
        self.assertTrue(hits, "the SQL skill's frozen rule should be findable")
        self.assertTrue(any("frozen" in h["text"].lower() for h in hits))


class TheLoop(unittest.TestCase):
    def setUp(self):
        self.patches = [
            mock.patch("api.assistant.org_backend", return_value=("postgres", "dbt")),
            mock.patch("api.database_routes._run",
                       return_value=(["Bill Cycle", "Billed Amount"], [["CYCLE1", 12.5]] * (MAX_ROWS + 3))),
            mock.patch("api.access_audit.record_access_event"),
        ]
        self.mocks = [p.start() for p in self.patches]

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _assistant(self, client):
        return Assistant(org_id="dev", org_name="Dev", actor_email="t@x", actor_id="t",
                         client_factory=lambda: client)

    def test_a_question_becomes_a_validated_query_and_an_answer(self):
        client = FakeClient([
            _resp([_tool("c1", "describe_canvas", {"canvas_id": "rpt_bill_segment"})], "tool_use"),
            _resp([_tool("c2", "run_sql", {"sql": 'select "Bill Cycle", "Billed Amount" from reporting.rpt_bill_segment limit 500',
                                          "purpose": "billed by cycle"})], "tool_use"),
            _resp([_text("Billed amounts by cycle are above.")], "end_turn"),
        ])
        out = self._assistant(client).ask("what was billed by cycle?")
        self.assertEqual(out["answer"], "Billed amounts by cycle are above.")
        self.assertEqual([s["tool"] for s in out["steps"]], ["describe_canvas", "run_sql"])
        self.assertTrue(all(s["ok"] for s in out["steps"]))
        q = out["queries"][0]
        self.assertEqual(q["row_count"], MAX_ROWS, "rows are capped")
        self.assertTrue(q["truncated"])
        self.assertEqual(q["columns"], ["Bill Cycle", "Billed Amount"])
        audit = self.mocks[2]
        self.assertEqual(audit.call_args.kwargs["action"], "assistant_sql")
        self.assertIn("billed by cycle", audit.call_args.kwargs["detail"])
        self.assertEqual(out["usage"], {"input_tokens": 30, "output_tokens": 15})
        # the system prompt names the org's canvases and carries the knowledge
        system = client.requests[0]["system"]
        self.assertIn("rpt_bill_segment", system[0]["text"])
        self.assertIn("Reference: cisadm-sql", system[1]["text"])
        self.assertEqual(system[1]["cache_control"], {"type": "ephemeral"})

    def test_a_refused_statement_goes_back_to_the_model_as_an_error_and_never_runs(self):
        client = FakeClient([
            # a statement the WORKSPACE would allow (cisadm is in its scope, no secret named):
            # only the assistant's own canvases-only fence stands between it and the data
            _resp([_tool("c1", "run_sql", {"sql": "select acct_id from cisadm.ci_acct", "purpose": "x"})], "tool_use"),
            _resp([_text("I can only read the reporting canvases.")], "end_turn"),
        ])
        out = self._assistant(client).ask("read the accounts table")
        self.assertEqual(out["steps"], [{"tool": "run_sql", "input": mock.ANY, "ok": False}])
        self.assertEqual(out["queries"], [], "nothing ran")
        self.mocks[1].assert_not_called()
        result = client.requests[1]["messages"][-1]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("not a reporting canvas", result["content"])
        self.assertEqual(self.mocks[2].call_args.kwargs["action"], "assistant_sql_refused")

    def test_the_loop_stops_at_the_turn_cap(self):
        forever = _resp([_tool("c", "list_canvases", {})], "tool_use")
        client = FakeClient([forever] * (MAX_TURNS + 5))
        out = self._assistant(client).ask("loop")
        self.assertEqual(len(client.requests), MAX_TURNS + 1)
        self.assertIn("too many steps", out["answer"])

    def test_the_returned_thread_stubs_tool_results_and_can_be_sent_back(self):
        client = FakeClient([
            _resp([_tool("c1", "list_canvases", {})], "tool_use"),
            _resp([_text("ok")], "end_turn"),
        ])
        out = self._assistant(client).ask("list")
        stubs = [b for m in out["thread"] if isinstance(m["content"], list)
                 for b in m["content"] if b.get("type") == "tool_result"]
        self.assertTrue(stubs and all("omitted" in b["content"] for b in stubs))
        json.dumps(out["thread"])   # serialisable for the browser
        follow = FakeClient([_resp([_text("again")], "end_turn")])
        self._assistant(follow).ask("and?", out["thread"])
        self.assertEqual(follow.requests[0]["messages"][-1], {"role": "user", "content": "and?"})


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.auth import init_auth_database
        from api.assistant_routes import router
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev",
            "WAREHOUSE_DATABASE_URL": "postgresql://test@localhost/test"})
        cls._env.start()
        init_auth_database()
        app = FastAPI()
        app.include_router(router)
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_unconfigured_is_a_503_that_says_what_to_set(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}):
            self.assertEqual(self.client.get("/portal/assistant/status").json(), {"configured": False, "model": None})
            r = self.client.post("/portal/assistant", json={"question": "hi"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("ANTHROPIC_API_KEY", r.json()["detail"])

    def test_configured_asks_the_assistant_for_this_org(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), \
             mock.patch("api.assistant_routes.Assistant") as A:
            A.return_value.ask.return_value = {"answer": "42", "steps": [], "queries": [], "thread": []}
            r = self.client.post("/portal/assistant", json={"question": "how many?"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["answer"], "42")
        self.assertEqual(A.call_args.kwargs["org_id"], "dev")
        A.return_value.ask.assert_called_once_with("how many?", [])

    def test_a_model_api_failure_says_what_the_api_said(self):
        # the first real call failed with "credit balance is too low"; a bare 502 with the
        # exception class name sent us to the server logs to learn that
        class BadRequestError(Exception):
            __module__ = "anthropic"
            message = "Error code: 400 - Your credit balance is too low to access the Anthropic API."
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), \
             mock.patch("api.assistant_routes.Assistant") as A:
            A.return_value.ask.side_effect = BadRequestError()
            r = self.client.post("/portal/assistant", json={"question": "how many?"})
        self.assertEqual(r.status_code, 502)
        self.assertIn("credit balance is too low", r.json()["detail"])
        self.assertIn("BadRequestError", r.json()["detail"])

    def test_an_empty_question_is_rejected(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}):
            self.assertEqual(self.client.post("/portal/assistant", json={"question": ""}).status_code, 422)


if __name__ == "__main__":
    unittest.main()


class TheStub(unittest.TestCase):
    """ASSISTANT_MODEL=stub exercises the whole path with no key -- and only outside production."""

    def test_stub_is_refused_in_production(self):
        from api import assistant
        with mock.patch.dict(os.environ, {"ASSISTANT_MODEL": "stub", "ENVIRONMENT": "production", "ANTHROPIC_API_KEY": ""}):
            self.assertFalse(assistant.stub_enabled())
            self.assertFalse(assistant.assistant_configured())
        with mock.patch.dict(os.environ, {"ASSISTANT_MODEL": "stub", "ENVIRONMENT": "development", "ANTHROPIC_API_KEY": ""}):
            self.assertTrue(assistant.assistant_configured())

    def test_stub_walks_the_real_tools_and_labels_itself(self):
        from api.assistant import StubModel
        with mock.patch("api.assistant.org_backend", return_value=("postgres", "dbt")), \
             mock.patch("api.database_routes._run", return_value=(["Year", "Rows"], [[2026, 5], [2025, 9]])) as run, \
             mock.patch("api.access_audit.record_access_event"):
            a = Assistant(org_id="dev", org_name="Dev", actor_email="t@x", actor_id="t", client_factory=StubModel)
            out = a.ask("how many bill segments were billed by year?")
        self.assertEqual([s["tool"] for s in out["steps"]], ["list_canvases", "describe_canvas", "run_sql"])
        self.assertIn("stub model", out["answer"])
        self.assertIn("rpt_bill_segment", run.call_args.args[1])
        self.assertEqual(out["queries"][0]["columns"], ["Year", "Rows"])

    def test_a_slow_query_comes_back_with_a_nudge(self):
        from api import assistant
        with mock.patch("api.database_routes._run", return_value=(["n"], [[1]])), \
             mock.patch("api.access_audit.record_access_event"), \
             mock.patch("api.assistant.time.perf_counter", side_effect=[0.0, 9.5]):
            out = assistant.tool_run_sql("dev", "postgres", "select 1 as n from reporting.rpt_bill", actor_email="t", actor_id="t", purpose="p")
        self.assertIn("9.5s", out["note"])


class FromInsideFunctions(unittest.TestCase):
    """FROM inside EXTRACT/SUBSTRING/TRIM is syntax, not a table source; a subquery's FROM is."""

    def test_functions_pass(self):
        for sql in ('SELECT EXTRACT(YEAR FROM "Bill Date") AS y, COUNT(*) FROM reporting.rpt_bill_segment GROUP BY 1',
                    'SELECT SUBSTRING("Account ID" FROM 1 FOR 3) FROM rpt_customer_account',
                    "SELECT TRIM(BOTH ' ' FROM \"Bill Cycle\") FROM ORIGINBA_REPORTING.rpt_bill",
                    'SELECT EXTRACT(MONTH FROM (SELECT MAX("Bill Date") FROM reporting.rpt_bill)) FROM reporting.rpt_bill_segment'):
            enforce_canvases_only(sql)

    def test_a_subquery_reading_cisadm_is_still_caught(self):
        for sql in ('SELECT EXTRACT(YEAR FROM "Bill Date") FROM reporting.rpt_bill WHERE 1 = (SELECT 1 FROM cisadm.ci_bill)',
                    'SELECT 1 FROM (SELECT * FROM cisadm.ci_acct) x'):
            with self.assertRaises(SqlWorkspaceValidationError, msg=sql):
                enforce_canvases_only(sql)
