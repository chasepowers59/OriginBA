"""POST /portal/assistant -- ask the analytics assistant a question about this org's data."""
from __future__ import annotations

from typing import Any

from api.auth.workstream_access import can_access_snapshot
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import json
import os
import queue
import threading

from api.assistant import (Assistant, assistant_configured, model_name, questions_last_minute, spend_report,
                           spend_today)
from api.auth.dependencies import AuthContext, get_auth_context
from api.org_db import require_org_for_data
from api.row_security import require_unrestricted

router = APIRouter(prefix="/portal/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    thread: list[dict[str, Any]] = Field(default_factory=list)
    # The page the question was asked from: {canvas_id, period, filters}. Optional.
    context: dict[str, Any] | None = None


@router.get("/status")
def status(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("nlq:read")
    return {"configured": assistant_configured(), "model": model_name() if assistant_configured() else None}


@router.get("/spend")
def spend(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    """Today's token spend for the caller's organization, per person, against the daily budget."""
    ctx.require_permission("nlq:read")
    return spend_report(require_org_for_data(ctx))


def _assistant_for(ctx: AuthContext) -> Assistant:
    """Checks, limits, and the assistant for this person: shared by the plain and streaming asks."""
    ctx.require_permission("nlq:read")
    require_unrestricted(ctx)   # the assistant writes its own SQL, which cannot carry row rules
    org_id = require_org_for_data(ctx)
    if not assistant_configured():
        raise HTTPException(status_code=503, detail="The assistant is not configured: set ANTHROPIC_API_KEY.")
    _within_limits(org_id, ctx.email)
    # A person granted some workstreams asks about those canvases only, as everywhere else.
    unrestricted = not ctx.workstreams or "*" in ctx.workstreams
    return Assistant(org_id=org_id, org_name=ctx.organization_name or org_id,
                     actor_email=ctx.email, actor_id=ctx.id,
                     can_read=None if unrestricted else (lambda cid: can_access_snapshot(ctx, cid)))


def _model_api_failure(exc: Exception) -> str | None:
    """The API's own message is the actionable part (billing, an invalid model id, a
    malformed request); the class name alone sent us to the server logs."""
    if "anthropic" not in type(exc).__module__:
        return None
    body = getattr(exc, "body", None)
    said = (body.get("error", {}).get("message") if isinstance(body, dict) else None) or str(exc)
    return f"The model API failed ({type(exc).__name__}): {said[:300]}"


@router.post("")
def ask(body: AskRequest, ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    assistant = _assistant_for(ctx)
    try:
        return assistant.ask(body.question, body.thread, body.context)
    except Exception as exc:  # noqa: BLE001 -- the model API is an external dependency
        detail = _model_api_failure(exc)
        if detail:
            raise HTTPException(status_code=502, detail=detail) from exc
        raise


@router.post("/stream")
def ask_streaming(body: AskRequest, ctx: AuthContext = Depends(get_auth_context)) -> StreamingResponse:
    """The same question as POST, as server-sent events: a `step` and `step_done` per tool
    call while the model works, then one `answer` (the POST body) or one `error`."""
    assistant = _assistant_for(ctx)
    events: queue.Queue = queue.Queue()

    def work() -> None:
        try:
            result = assistant.ask(body.question, body.thread, body.context, on_event=events.put)
            events.put({"type": "answer", **result})
        except Exception as exc:  # noqa: BLE001
            events.put({"type": "error", "detail": _model_api_failure(exc) or "The assistant could not answer."})
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def sse():
        while (event := events.get()) is not None:
            kind = event.pop("type")
            yield f"event: {kind}\ndata: {json.dumps(event, default=str)}\n\n"

    # no-transform/no buffering: a proxy that buffers the body turns progress back into a wait
    return StreamingResponse(sse(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"})



def _within_limits(org_id: str, actor_email: str) -> None:
    """Two caps, both read from the audit rows every question writes (docs/assistant_token_budget.md):
    ASSISTANT_DAILY_TOKEN_BUDGET  input-equivalent tokens per organization per UTC day
    ASSISTANT_QUESTIONS_PER_MINUTE  questions per person per minute
    Unset means no cap. A refusal says which cap, so the person knows whether to wait a minute
    or until tomorrow."""
    budget = os.getenv("ASSISTANT_DAILY_TOKEN_BUDGET", "").strip()
    if budget and spend_today(org_id) >= int(budget):
        raise HTTPException(status_code=429, detail=f"Today's assistant budget for this organization "
                                                    f"({int(budget):,} tokens) is used up; it resets at midnight UTC.")
    per_minute = os.getenv("ASSISTANT_QUESTIONS_PER_MINUTE", "").strip()
    if per_minute and questions_last_minute(actor_email) >= int(per_minute):
        raise HTTPException(status_code=429, detail=f"More than {per_minute} question(s) in the last minute; "
                                                    f"wait a moment and ask again.")
