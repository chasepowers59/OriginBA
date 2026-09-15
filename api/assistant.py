"""The analytics assistant: a tool-using Claude that answers questions about a tenant's data
by reading the canvases it is allowed to see and running SQL through the same validated,
scoped, audited path the SQL workspace uses.

What it can do is bounded by its tools, not by its instructions:

    list_canvases        the reporting canvases this organization actually has
    describe_canvas      every column of one canvas, with type, role and meaning
    run_sql              validated -> fenced to reporting canvases -> scoped to the org
                         -> row-capped -> audited. The ONLY way it reaches data.
    search_knowledge     the C2M skills and the canvas descriptions, for "where do I look"

Canvases only (Chase, 2026-09-15): the workspace fence admits CISADM too, so run_sql adds
a stricter one -- every table the statement reads must be an rpt_* canvas -- and refuses
the rest with a message the model can act on.

The system prompt is the same knowledge a Claude Code session loads to write CISADM SQL
(api/assistant_knowledge, copied from the dbt repo's skills), plus this organization's
catalog. Unset ANTHROPIC_API_KEY means "not configured", answered as a 503, never a
fallback.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

from api.snapshot_catalog import load_catalog, org_backend
from api.sql_workspace_validator import SqlWorkspaceValidationError, strip_sql_noise

KNOWLEDGE = Path(__file__).resolve().parent / "assistant_knowledge"
DEFAULT_MODEL = "claude-sonnet-5"
MAX_TURNS = 8            # tool calls per question; the loop stops rather than run away
MAX_ROWS = 200           # rows a single run_sql returns to the model and the reader
MAX_THREAD = 20          # prior messages kept for a follow-up
MAX_TOKENS = 2048


def assistant_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def model_name() -> str:
    return os.getenv("ASSISTANT_MODEL") or DEFAULT_MODEL


# ---------------------------------------------------------------- the canvases-only fence
_READ_TARGET = re.compile(
    r'\b(?:FROM|JOIN)\s+("?[\w$#]+"?)(?:\s*\.\s*("?[\w$#]+"?))?', re.IGNORECASE)
_CANVAS_SCHEMAS = {"reporting", "originba_reporting"}


def enforce_canvases_only(sql: str) -> None:
    """Every table the statement reads must be a reporting canvas (rpt_*)."""
    cleaned = strip_sql_noise(sql)
    for schema, table in _READ_TARGET.findall(cleaned):
        if table:
            s, t = schema.strip('"').lower(), table.strip('"').lower()
            if s not in _CANVAS_SCHEMAS or not t.startswith("rpt_"):
                raise SqlWorkspaceValidationError(
                    f"{schema}.{table} is not a reporting canvas. The assistant reads the "
                    f"rpt_* canvases only; use list_canvases to see them.")
        else:
            t = schema.strip('"').lower()
            if not t.startswith("rpt_"):
                raise SqlWorkspaceValidationError(
                    f"{schema} is not a reporting canvas. The assistant reads the rpt_* "
                    f"canvases only; use list_canvases to see them.")


# ---------------------------------------------------------------- the tools
TOOLS: list[dict[str, Any]] = [
    {"name": "list_canvases",
     "description": "The reporting canvases this organization has: id, label, workstream, "
                    "grain and a one-line summary. Start here when you do not know which "
                    "canvas answers the question.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "describe_canvas",
     "description": "Every column of one canvas with its type, role (dimension or measure) "
                    "and meaning, plus its date fields and the exact table name to query. "
                    "Always call this before writing SQL against a canvas; never guess a "
                    "column name.",
     "input_schema": {"type": "object",
                      "properties": {"canvas_id": {"type": "string", "description": "e.g. rpt_bill_segment"}},
                      "required": ["canvas_id"]}},
    {"name": "run_sql",
     "description": "Run a read-only SELECT against the reporting canvases and get the rows "
                    "back (capped). Column names are Title Case with spaces and MUST be "
                    "double-quoted exactly as describe_canvas lists them. Qualify the table "
                    "with the schema you were given. Add a row limit. If the statement is "
                    "refused, the message says why: fix it and run again.",
     "input_schema": {"type": "object",
                      "properties": {"sql": {"type": "string"},
                                     "purpose": {"type": "string", "description": "one line: what this query establishes"}},
                      "required": ["sql", "purpose"]}},
    {"name": "search_knowledge",
     "description": "Search the C2M reference notes (SQL traps, business processes, what a "
                    "status means, which canvas holds what) and the canvas column "
                    "descriptions. Use it for 'where would I find', 'what does X mean', and "
                    "before assuming a business rule.",
     "input_schema": {"type": "object",
                      "properties": {"query": {"type": "string"}},
                      "required": ["query"]}},
]


def _canvases(org_id: str) -> dict[str, dict[str, Any]]:
    cat = load_catalog(organization_id=org_id)
    enabled = set(cat.get("portal_snapshots") or cat["snapshots"].keys())
    return {k: v for k, v in cat["snapshots"].items() if k in enabled}


def _table_ref(engine: str, entry: dict[str, Any]) -> str:
    table = entry.get("table_name") or entry.get("id")
    return f"ORIGINBA_REPORTING.{table}" if engine == "oracle_dbt" else f"reporting.{table}"


def tool_list_canvases(org_id: str, engine: str) -> list[dict[str, Any]]:
    return [{"id": k, "label": v.get("label"), "workstream": v.get("workstream_label") or v.get("workstream"),
             "grain": v.get("grain_description") or v.get("grain"), "summary": v.get("summary"),
             "table": _table_ref(engine, v)}
            for k, v in sorted(_canvases(org_id).items())]


def tool_describe_canvas(org_id: str, engine: str, canvas_id: str) -> dict[str, Any]:
    entry = _canvases(org_id).get((canvas_id or "").strip().lower())
    if not entry:
        return {"error": f"{canvas_id} is not a canvas this organization has; call list_canvases."}
    return {
        "id": canvas_id, "label": entry.get("label"), "table": _table_ref(engine, entry),
        "grain": entry.get("grain_description") or entry.get("grain"),
        "summary": entry.get("summary"), "usage_guidance": entry.get("usage_guidance"),
        "date_fields": [d.get("id") if isinstance(d, dict) else d for d in entry.get("date_fields") or []],
        "default_date_field": entry.get("default_date_field"),
        "columns": [{"name": f.get("id"), "type": f.get("type"), "role": f.get("role"),
                     "meaning": f.get("description")} for f in entry.get("fields") or []],
        "related_canvas": entry.get("related_snapshot"),
    }


def tool_search_knowledge(org_id: str, query: str, limit: int = 8) -> list[dict[str, str]]:
    """Keyword search: paragraphs of the knowledge files and canvas column descriptions,
    scored by how many query words they carry. Small, honest, and no vector store to run."""
    words = [w for w in re.findall(r"[a-z0-9_]+", (query or "").lower()) if len(w) > 2]
    if not words:
        return []
    hits: list[tuple[int, dict[str, str]]] = []
    for f in sorted(KNOWLEDGE.glob("*.md")):
        for para in re.split(r"\n\s*\n", f.read_text()):
            text = para.strip()
            if len(text) < 40 or text.startswith("<!--"):
                continue
            score = sum(1 for w in words if w in text.lower())
            if score:
                hits.append((score, {"source": f.stem, "text": text[:700]}))
    for k, v in _canvases(org_id).items():
        for fld in v.get("fields") or []:
            d = fld.get("description") or ""
            blob = f"{k} {fld.get('id')} {d}".lower()
            score = sum(1 for w in words if w in blob)
            if score >= max(1, len(words) - 1):
                hits.append((score, {"source": f"canvas {k}", "text": f"{fld.get('id')}: {d}"}))
    hits.sort(key=lambda h: -h[0])
    return [h[1] for h in hits[:limit]]


def tool_run_sql(org_id: str, engine: str, sql: str, *, actor_email: str, actor_id: str | None,
                 purpose: str) -> dict[str, Any]:
    from api.access_audit import record_access_event
    from api.database_routes import _run, _validate
    try:
        validated = _validate(engine, sql)
        enforce_canvases_only(validated)
    except SqlWorkspaceValidationError as exc:
        record_access_event(actor_email=actor_email, actor_id=actor_id, action="assistant_sql_refused",
                            target_type="sql", target_id=org_id, detail=f"{exc} | sql: {sql[:300]}")
        return {"error": str(exc)}
    started = time.perf_counter()
    columns, rows = _run(engine, validated, org_id, MAX_ROWS + 1)
    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    ms = int((time.perf_counter() - started) * 1000)
    record_access_event(actor_email=actor_email, actor_id=actor_id, action="assistant_sql",
                        target_type="sql", target_id=org_id,
                        detail=f"rows={len(rows)}; ms={ms}; purpose: {purpose[:120]}; sql: {validated[:300]}")
    return {"columns": columns, "rows": [[_cell(v) for v in r] for r in rows],
            "row_count": len(rows), "truncated": truncated, "ms": ms, "sql": validated}


def _cell(v: Any) -> Any:
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    return str(v)


# ---------------------------------------------------------------- the prompt
def _knowledge_text() -> str:
    parts = []
    for f in sorted(KNOWLEDGE.glob("*.md")):
        if f.name == "README.md":
            continue
        parts.append(f"\n\n# Reference: {f.stem}\n\n{f.read_text()}")
    return "".join(parts)


def system_prompt(org_id: str, org_name: str, engine: str) -> list[dict[str, Any]]:
    canvases = tool_list_canvases(org_id, engine)
    listing = "\n".join(f"- {c['id']} ({c['label']}, {c['workstream']}): {c['grain']}. {c['summary'] or ''}"
                        for c in canvases)
    quoting = ('reporting.rpt_bill_segment' if engine == "postgres" else 'ORIGINBA_REPORTING.rpt_bill_segment')
    limit = "LIMIT 50" if engine == "postgres" else "FETCH FIRST 50 ROWS ONLY"
    head = f"""You are the OriginBA analytics assistant for {org_name}, a utility running Oracle C2M.
You answer questions about their data by reading their reporting canvases and running SQL.

How you work:
1. Find the canvas: use list_canvases, then describe_canvas. Never guess a column name; every
   column is Title Case with spaces and must be double-quoted exactly as listed.
2. Write a read-only SELECT against the canvas table exactly as describe_canvas names it, e.g.
   SELECT "Account ID", "Billed Amount" FROM {quoting} WHERE "Bill Date" >= DATE '2026-01-01' {limit}
   The engine is {'PostgreSQL' if engine == 'postgres' else 'Oracle'}. Always add a row limit.
3. Run it with run_sql. If it is refused, read the reason, fix the statement, run again.
4. Answer in plain language first: the number or the list, what it covers (which canvas, which
   date window, which filters), and any caveat from the reference notes (frozen vs unfrozen,
   final vs initial measurements, units, grain). Then show the SQL you ran.

Rules you never break:
- Reporting canvases (rpt_*) only. Never CISADM tables, never other schemas.
- Only frozen bill segments and financial transactions are money; only final measurements are
  billable reads; usage is additive only within one unit of measure; lifecycle statuses are
  base product, every other code is this client's own configuration.
- If the question cannot be answered from the canvases, say so and point to the right place:
  the SQL workspace for ad hoc SQL, the report builder for a saved view, or which canvas
  would need extending. Never invent a figure.
- Keep answers short. A sentence of answer, a sentence of scope, the caveat if any, the SQL.

The organization's canvases:
{listing}
"""
    return [
        {"type": "text", "text": head},
        {"type": "text", "text": _knowledge_text(), "cache_control": {"type": "ephemeral"}},
    ]


# ---------------------------------------------------------------- the loop
class Assistant:
    def __init__(self, *, org_id: str, org_name: str, actor_email: str, actor_id: str | None,
                 client_factory: Callable[[], Any] | None = None):
        self.org_id, self.org_name = org_id, org_name
        self.actor_email, self.actor_id = actor_email, actor_id
        engine, _ = org_backend(org_id)
        self.engine = "postgres" if engine == "postgres" else "oracle_dbt"
        self._client_factory = client_factory or self._anthropic

    @staticmethod
    def _anthropic():
        import anthropic
        return anthropic.Anthropic()

    def _dispatch(self, name: str, args: dict[str, Any]) -> Any:
        if name == "list_canvases":
            return tool_list_canvases(self.org_id, self.engine)
        if name == "describe_canvas":
            return tool_describe_canvas(self.org_id, self.engine, args.get("canvas_id", ""))
        if name == "search_knowledge":
            return tool_search_knowledge(self.org_id, args.get("query", ""))
        if name == "run_sql":
            return tool_run_sql(self.org_id, self.engine, args.get("sql", ""), actor_email=self.actor_email,
                                actor_id=self.actor_id, purpose=args.get("purpose", ""))
        return {"error": f"unknown tool {name}"}

    def ask(self, question: str, thread: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        client = self._client_factory()
        messages = list(thread or [])[-MAX_THREAD:] + [{"role": "user", "content": question}]
        system = system_prompt(self.org_id, self.org_name, self.engine)
        steps: list[dict[str, Any]] = []
        queries: list[dict[str, Any]] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        answer = ""
        for _ in range(MAX_TURNS + 1):
            resp = client.messages.create(model=model_name(), max_tokens=MAX_TOKENS, system=system,
                                          tools=TOOLS, messages=messages)
            u = getattr(resp, "usage", None)
            if u:
                usage["input_tokens"] += getattr(u, "input_tokens", 0) or 0
                usage["output_tokens"] += getattr(u, "output_tokens", 0) or 0
            content = [_block_dict(b) for b in resp.content]
            messages.append({"role": "assistant", "content": content})
            text = "\n".join(b["text"] for b in content if b["type"] == "text").strip()
            if text:
                answer = text
            calls = [b for b in content if b["type"] == "tool_use"]
            if resp.stop_reason != "tool_use" or not calls:
                break
            results = []
            for call in calls:
                out = self._dispatch(call["name"], call["input"] or {})
                is_error = isinstance(out, dict) and "error" in out
                steps.append({"tool": call["name"], "input": _brief(call["input"]), "ok": not is_error})
                if call["name"] == "run_sql" and not is_error:
                    queries.append({"purpose": call["input"].get("purpose", ""), **out})
                results.append({"type": "tool_result", "tool_use_id": call["id"],
                                "content": json.dumps(out, default=str)[:60000], "is_error": is_error})
            messages.append({"role": "user", "content": results})
        else:
            answer = answer or "I stopped after too many steps without an answer. Try a narrower question."
        return {"answer": answer, "steps": steps, "queries": queries, "model": model_name(),
                "usage": usage, "thread": _trim_thread(messages)}


def _block_dict(b: Any) -> dict[str, Any]:
    if getattr(b, "type", None) == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input or {})}
    return {"type": "text", "text": getattr(b, "text", "") or ""}


def _brief(inp: Any) -> str:
    s = json.dumps(inp, default=str)
    return s if len(s) <= 200 else s[:197] + "..."


def _trim_thread(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The thread a client sends back for a follow-up. Tool results are replaced by a stub:
    the model can re-run anything it needs, and rows do not belong in a browser round trip."""
    out = []
    for m in messages[-MAX_THREAD:]:
        c = m["content"]
        if isinstance(c, list):
            c = [({**b, "content": "(result omitted; re-run the tool if needed)"}
                  if b.get("type") == "tool_result" else b) for b in c]
        out.append({"role": m["role"], "content": c})
    return out
