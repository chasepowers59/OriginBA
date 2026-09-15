# The analytics assistant

`POST /portal/assistant` answers a question about the signed-in organization's data by reading
its reporting canvases and running SQL. It is a tool-using Claude; what it can reach is bounded
by its tools, not by its instructions.

## Tools

| Tool | What it does |
| --- | --- |
| `list_canvases` | the `rpt_*` canvases this organization has (from its catalog), with grain, summary and the exact table to query |
| `describe_canvas` | every column of one canvas with type, role and meaning, plus date fields |
| `run_sql` | validated by the SQL workspace's validator (read-only, secrets guard, engine fence), then **fenced to `rpt_*` canvases only**, scoped to the organization, capped at 200 rows, audited as `assistant_sql` / `assistant_sql_refused` with the question's purpose |
| `search_knowledge` | keyword search over the C2M skills (`api/assistant_knowledge/`) and the canvas column descriptions |

`run_sql` is the only path to data, and it is the same `_validate` / `_run` pair the SQL
workspace uses, so the assistant can do nothing a user could not do in the workspace, and
strictly less: the workspace admits CISADM, the assistant does not (Chase, 2026-09-15).

## What it knows

The system prompt is this organization's canvas list plus the same skills a Claude Code session
loads to write CISADM SQL: `cisadm-sql`, `c2m-functional-architect` and its body of knowledge.
They are copied from `originba_dbt/.claude/skills` by `scripts/local/sync_assistant_knowledge.py`
so the API image is self-contained; re-run it when the skills change. The knowledge block is
sent with prompt caching, so it is paid for once per cache window, not per question.

## Configuration

| Variable | |
| --- | --- |
| `ANTHROPIC_API_KEY` | required; unset means `/portal/assistant/status` reports `configured: false` and `POST` answers 503 |
| `ASSISTANT_MODEL` | default `claude-sonnet-5`. `stub` (development only, refused in production) is a scripted stand-in that lists the canvases, picks one by name, runs one aggregate on its default date field, and labels every answer as the stub -- so the whole path can be exercised with no key |

Permission: `nlq:read`. The organization comes from the auth context, never from the request.

## Request and response

```json
POST /portal/assistant
{ "question": "how much was billed by cycle in the last 90 days?", "thread": [] }

{ "answer": "...", "steps": [{"tool": "describe_canvas", "input": "...", "ok": true}, ...],
  "queries": [{"purpose": "...", "sql": "...", "columns": [...], "rows": [...], "row_count": 50, "truncated": false, "ms": 84}],
  "model": "claude-sonnet-5", "usage": {"input_tokens": 0, "output_tokens": 0},
  "thread": [ ...send back as `thread` for a follow-up... ] }
```

The returned thread has tool results replaced by a stub; the model re-runs what it needs.
The loop stops after 8 tool calls and says so rather than run on.

## Tests

`tests/test_assistant.py` runs without a key or a network: a fake model client scripts the tool
calls, the executor is patched, the catalog is real. It proves the canvases-only fence, the
validated path, the row cap, the audit, the loop cap, and the routes' answers when unconfigured.

## Measured (Ellensburg 25.4, 2026-09-15)

Driven from the browser as the Ellensburg organization (Oracle, in-database warehouse, over the VPN):

| | |
| --- | --- |
| list / describe / prompt build / knowledge search | 0-3 ms each (in-process; catalog and knowledge cached) |
| system prompt | ~50,000 chars, ~12,500 tokens, sent with prompt caching |
| bill segments by year (1.3M+ segments, aggregate) | 1,072 ms cold, 51 ms warm (Oracle pool + result cache) |
| a 300-row detail with ORDER BY over the whole canvas | 5,800 ms -- the prompt now steers away from this shape |
| request round trip, warm | 103 ms; answer payload 3 KB; `/status` 13 ms |
| a CISADM read | refused in 0 ms, before any connection |

Statement timeouts already exist below the assistant: 30 s on Postgres (`SET LOCAL statement_timeout`)
and the Oracle call timeout on the pooled session. A query slower than 8 s comes back to the model
with a note to narrow it. In development, React StrictMode fetches `/status` twice on mount; that
is a development-only double effect, not a production cost.
