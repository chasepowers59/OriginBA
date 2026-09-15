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
| `ASSISTANT_MODEL` | default `claude-sonnet-5` |

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
