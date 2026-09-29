"""GET /portal/health -- what this API process has been doing, for administrators: requests,
errors and time per route, the slowest recent requests, the last server errors by reference,
the result cache, and each organization's warehouse build stamp. In memory and per process:
it starts empty when the API restarts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api import data_version, request_tracing, summary_cache
from api.auth.dependencies import AuthContext, get_auth_context

router = APIRouter(prefix="/portal/health", tags=["health"])


@router.get("")
def system_health(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="System health is for administrators.")
    return {**request_tracing.snapshot(), "cache": summary_cache.stats(), "data_versions": data_version.known()}
