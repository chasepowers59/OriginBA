"""POST /portal/assistant -- ask the analytics assistant a question about this org's data."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.assistant import Assistant, assistant_configured, model_name
from api.auth.dependencies import AuthContext, get_auth_context
from api.org_db import require_org_for_data

router = APIRouter(prefix="/portal/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    thread: list[dict[str, Any]] = Field(default_factory=list)


@router.get("/status")
def status(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("nlq:read")
    return {"configured": assistant_configured(), "model": model_name() if assistant_configured() else None}


@router.post("")
def ask(body: AskRequest, ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("nlq:read")
    org_id = require_org_for_data(ctx)
    if not assistant_configured():
        raise HTTPException(status_code=503, detail="The assistant is not configured: set ANTHROPIC_API_KEY.")
    assistant = Assistant(org_id=org_id, org_name=ctx.organization_name or org_id,
                          actor_email=ctx.email, actor_id=ctx.id)
    try:
        return assistant.ask(body.question, body.thread)
    except Exception as exc:  # noqa: BLE001 -- the model API is an external dependency
        name = type(exc).__name__
        if "anthropic" in type(exc).__module__:
            raise HTTPException(status_code=502, detail=f"The model API failed ({name}). Try again.") from exc
        raise
