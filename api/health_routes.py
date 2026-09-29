"""GET /portal/health -- what this API process has been doing, for administrators: requests,
errors and time per route, the slowest recent requests, the last server errors by reference,
the result cache, each organization's warehouse build stamp and its last cache warm. In memory and per process:
it starts empty when the API restarts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api import cache_warmer, data_version, request_tracing, summary_cache
from api.auth.dependencies import AuthContext, get_auth_context

router = APIRouter(prefix="/portal/health", tags=["health"])


@router.get("")
def system_health(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="System health is for administrators.")
    return {**request_tracing.snapshot(), "cache": summary_cache.stats(), "data_versions": data_version.known(),
            "warmed": cache_warmer.status()}
