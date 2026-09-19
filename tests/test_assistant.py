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
        # one line per column, not one JSON object: rpt_bill_segment (110 columns) was 22.7K
        # chars / ~5.5K tokens as objects and is re-sent on every later turn of the question
        d = tool_describe_canvas("dev", "postgres", "rpt_bill_segment")
        lines = d["columns"].splitlines()
        self.assertEqual(len(lines), len([l for l in lines if l.count(" | ") == 3]), "name | type | role | meaning")
        self.assertTrue(any(l.startswith("Billed Amount | ") for l in lines))
        self.assertTrue(all(len(l) <= 160 for l in lines), "a meaning is one clause; the notes hold the rest")
        self.assertLess(len(json.dumps(d)), 13000)
        self.assertIn("error", tool_describe_canvas("dev", "postgres", "rpt_nope"))

    def test_the_prompt_fixes_the_date_window_and_does_not_repeat_sql(self):
        from api.assistant import system_prompt
        head = system_prompt("dev", "Dev", "oracle_dbt")[0]["text"]
        self.assertIn("TRUNC(SYSDATE) - 90", head)
        self.assertIn("Do not repeat the SQL", head)
        self.assertIn("CURRENT_DATE - 90", system_prompt("dev", "Dev", "postgres")[0]["text"])

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
        actions = [c.kwargs["action"] for c in self.mocks[2].call_args_list]
        self.assertEqual(actions, ["assistant_sql", "assistant_ask"], "the query, then the question with its cost")
        self.assertIn("billed by cycle", self.mocks[2].call_args_list[0].kwargs["detail"])
        self.assertEqual((out["usage"]["input_tokens"], out["usage"]["output_tokens"]), (30, 15))
        # the system prompt names the org's canvases and carries the knowledge
        system = client.requests[0]["system"]
        self.assertIn("rpt_bill_segment", system[0]["text"])
        self.assertEqual(system[-1]["cache_control"], {"type": "ephemeral"})

    def test_an_empty_text_block_never_goes_back_to_the_api(self):
        # the first real Sonnet turn came back as [text(""), tool_use]; echoing that
        # assistant content verbatim was a 400: "text content blocks must be non-empty"
        client = FakeClient([
            _resp([_text(""), _tool("t1", "list_canvases", {})], "tool_use"),
            _resp([_text("done")], "end_turn"),
        ])
        Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id=None,
                  client_factory=lambda: client).ask("hi")
        second_call = client.requests[1]["messages"]
        for m in second_call:
            for b in (m["content"] if isinstance(m["content"], list) else []):
                if b.get("type") == "text":
                    self.assertTrue(b["text"], "an empty text block was sent back")

    def test_the_cost_of_a_question_is_counted_in_full(self):
        # cached reads and cache writes are billed too (at 0.1x and 1.25x); counting only
        # input_tokens under-reported the first real question by roughly 5x
        def _usage(inp, out, read, write):
            return SimpleNamespace(input_tokens=inp, output_tokens=out,
                                   cache_read_input_tokens=read, cache_creation_input_tokens=write)
        r1 = SimpleNamespace(content=[_tool("t1", "list_canvases", {})], stop_reason="tool_use", usage=_usage(100, 20, 0, 22000))
        r2 = SimpleNamespace(content=[_text("done")], stop_reason="end_turn", usage=_usage(300, 50, 22000, 0))
        out = Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id=None,
                        client_factory=lambda: FakeClient([r1, r2])).ask("hi")
        self.assertEqual(out["usage"], {"input_tokens": 400, "output_tokens": 70,
                                        "cache_read_input_tokens": 22000, "cache_creation_input_tokens": 22000,
                                        "turns": 2})

    def test_the_conversation_prefix_is_cached_turn_by_turn(self):
        # every turn re-sends the whole message history; a moving cache breakpoint on the
        # latest user message makes each turn pay for its new tokens only
        client = FakeClient([
            _resp([_tool("t1", "list_canvases", {})], "tool_use"),
            _resp([_text("done")], "end_turn"),
        ])
        Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id=None,
                  client_factory=lambda: client).ask("hi")
        for req in client.requests:
            last = req["messages"][-1]["content"]
            block = last[-1] if isinstance(last, list) else None
            self.assertIsNotNone(block, "the user turn must be a block list so it can carry cache_control")
            self.assertEqual(block.get("cache_control"), {"type": "ephemeral"})
            self.assertEqual(sum(1 for m in req["messages"] for b in (m["content"] if isinstance(m["content"], list) else [])
                                 if b.get("cache_control")), 1, "one moving breakpoint, never one per turn")

    def test_the_model_sees_fewer_rows_than_the_screen(self):
        from api.assistant import MAX_ROWS_MODEL
        self.assertLess(MAX_ROWS_MODEL, MAX_ROWS)
        big = {"columns": ["n"], "rows": [[i] for i in range(MAX_ROWS)], "row_count": MAX_ROWS,
               "truncated": False, "ms": 1, "sql": "select 1", "integrity": []}
        client = FakeClient([
            _resp([_tool("t1", "run_sql", {"sql": "select 1", "purpose": "p"})], "tool_use"),
            _resp([_text("done")], "end_turn"),
        ])
        with mock.patch("api.assistant.tool_run_sql", return_value=big):
            out = Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id=None,
                            client_factory=lambda: client).ask("hi")
        sent = json.loads(client.requests[1]["messages"][-1]["content"][0]["content"])
        self.assertEqual(len(sent["rows"]), MAX_ROWS_MODEL)
        self.assertIn("rows_shown_to_model", sent)
        self.assertEqual(len(out["queries"][0]["rows"]), MAX_ROWS, "the screen still gets every row")

    def test_the_reference_notes_are_a_tool_not_a_prefix_unless_asked(self):
        # measured 2026-09-15: the notes are ~19.5K of the ~22.7K tokens every turn reads from
        # cache; the model reaches them through search_knowledge (it did so unprompted)
        from api.assistant import system_prompt
        with mock.patch.dict(os.environ, {"ASSISTANT_INLINE_KNOWLEDGE": ""}):
            blocks = system_prompt("dev", "Dev", "postgres")
        self.assertEqual(len(blocks), 1)
        self.assertLess(len(blocks[0]["text"]), 12000)
        self.assertEqual(blocks[0].get("cache_control"), {"type": "ephemeral"}, "the prefix is still cached")
        with mock.patch.dict(os.environ, {"ASSISTANT_INLINE_KNOWLEDGE": "1"}):
            blocks = system_prompt("dev", "Dev", "postgres")
        self.assertEqual(len(blocks), 2)
        self.assertGreater(len(blocks[1]["text"]), 20000)

    def test_the_cache_ttl_is_a_setting(self):
        # sporadic use (a question every 10-40 min) rewrites a 5-minute cache on every
        # question; the 1-hour TTL costs 2x on the write and pays back from the second question
        from api.assistant import cache_control
        with mock.patch.dict(os.environ, {"ASSISTANT_CACHE_TTL": ""}):
            self.assertEqual(cache_control(), {"type": "ephemeral"})
        with mock.patch.dict(os.environ, {"ASSISTANT_CACHE_TTL": "1h"}):
            self.assertEqual(cache_control(), {"type": "ephemeral", "ttl": "1h"})
            client = FakeClient([_resp([_text("ok")], "end_turn")])
            Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id=None,
                      client_factory=lambda: client).ask("hi")
            req = client.requests[0]
            self.assertEqual(req["system"][-1]["cache_control"], {"type": "ephemeral", "ttl": "1h"})
            self.assertEqual(req["messages"][-1]["content"][-1]["cache_control"], {"type": "ephemeral", "ttl": "1h"})

    def test_every_question_is_audited_with_its_token_cost(self):
        client = FakeClient([_resp([_text("ok")], "end_turn")])
        with mock.patch("api.access_audit.record_access_event") as rec:
            Assistant(org_id="dev", org_name="Dev", actor_email="a@b", actor_id="u1",
                      client_factory=lambda: client).ask("how many bills?")
        asks = [c for c in rec.call_args_list if c.kwargs.get("action") == "assistant_ask"]
        self.assertEqual(len(asks), 1)
        d = asks[0].kwargs["detail"]
        self.assertIn("input_tokens=10", d)
        self.assertIn("output_tokens=5", d)
        self.assertIn("turns=1", d)
        self.assertIn("how many bills?", d)
        self.assertEqual(asks[0].kwargs["target_id"], "dev")

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
        self.assertIn("assistant_sql_refused", [c.kwargs["action"] for c in self.mocks[2].call_args_list])

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
        sent = follow.requests[0]["messages"]
        self.assertEqual(sent[-1], {"role": "user", "content": [{"type": "text", "text": "and?", "cache_control": {"type": "ephemeral"}}]})
        self.assertEqual(sent[:-1], out["thread"], "the thread goes back exactly as it was handed out")


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
            body = {"type": "error", "error": {"type": "invalid_request_error",
                    "message": "Your credit balance is too low to access the Anthropic API."}}
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only"}), \
             mock.patch("api.assistant_routes.Assistant") as A:
            A.return_value.ask.side_effect = BadRequestError()
            r = self.client.post("/portal/assistant", json={"question": "how many?"})
        self.assertEqual(r.status_code, 502)
        self.assertIn("credit balance is too low", r.json()["detail"])
        self.assertIn("BadRequestError", r.json()["detail"])

    def _spend(self, org, actor, **usage):
        from api.access_audit import record_access_event
        u = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
             "cache_creation_input_tokens": 0, "turns": 1} | usage
        record_access_event(actor_email=actor, actor_id=None, action="assistant_ask", target_type="assistant",
                            target_id=org, detail="; ".join(f"{k}={v}" for k, v in u.items()) + "; question: q")

    def test_spend_is_read_back_from_the_audit_in_input_equivalents(self):
        from api.assistant import spend_today, input_equivalent
        self.assertEqual(input_equivalent({"input_tokens": 100, "cache_creation_input_tokens": 1000,
                                           "cache_read_input_tokens": 10000, "output_tokens": 200}),
                         100 + 1250 + 1000 + 1000)
        before = spend_today("org-spend")
        self._spend("org-spend", "x@y", input_tokens=10, cache_read_input_tokens=1000, output_tokens=20)
        self._spend("org-spend", "z@y", cache_creation_input_tokens=800)
        self._spend("org-other", "x@y", input_tokens=99999)
        self.assertEqual(spend_today("org-spend") - before, 10 + 100 + 100 + 1000)

    def test_a_daily_budget_answers_429_and_says_so(self):
        self._spend("dev", "budget@y", input_tokens=5000)
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only", "ASSISTANT_DAILY_TOKEN_BUDGET": "100"}), \
             mock.patch("api.assistant_routes.Assistant") as A:
            r = self.client.post("/portal/assistant", json={"question": "how many?"})
        self.assertEqual(r.status_code, 429)
        self.assertIn("budget", r.json()["detail"])
        A.return_value.ask.assert_not_called()

    def test_a_person_is_rate_limited_per_minute(self):
        from api.assistant import questions_last_minute
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-only", "ASSISTANT_QUESTIONS_PER_MINUTE": "1",
                                          "ASSISTANT_DAILY_TOKEN_BUDGET": ""}), \
             mock.patch("api.assistant_routes.Assistant") as A:
            A.return_value.ask.side_effect = lambda q, t: (self._spend("dev", "dev@origin.local", input_tokens=1)
                                                           or {"answer": "42", "steps": [], "queries": [], "thread": []})
            first = self.client.post("/portal/assistant", json={"question": "one"})
            second = self.client.post("/portal/assistant", json={"question": "two"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertIn("minute", second.json()["detail"])
        self.assertGreaterEqual(questions_last_minute("dev@origin.local"), 1)

    def test_spend_is_visible_per_day_and_per_person(self):
        self._spend("dev", "a@origin.local", input_tokens=1000)
        self._spend("dev", "b@origin.local", output_tokens=100)   # 500 equivalent
        r = self.client.get("/portal/assistant/spend")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["organization"], "dev")
        self.assertGreaterEqual(body["today"], 1500)
        by = {p["actor"]: p for p in body["people"]}
        self.assertGreaterEqual(by["a@origin.local"]["tokens"], 1000)
        self.assertGreaterEqual(by["b@origin.local"]["questions"], 1)
        self.assertIn("budget", body)   # null when no cap is set

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
