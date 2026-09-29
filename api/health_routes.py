"""GET /portal/health -- what this API process has been doing, for administrators: requests,
errors and time per route, the slowest recent requests, the last server errors by reference,
the result cache, each organization's warehouse build stamp, last build and last cache warm. In memory and per process:
it starts empty when the API restarts."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api import cache_warmer, data_version, request_tracing, summary_cache
from api.auth.dependencies import AuthContext, get_auth_context
from api.freshness import freshness

router = APIRouter(prefix="/portal/health", tags=["health"])


@router.get("")
def system_health(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    if ctx.role != "admin":
        raise HTTPException(status_code=403, detail="System health is for administrators.")
    known = data_version.known()
    return {**request_tracing.snapshot(), "cache": summary_cache.stats(), "data_versions": known,
            "warmed": cache_warmer.status(),
            # when each organization this process has read was last built, and whether that is stale
            "freshness": {org: _freshness_or_none(org) for org in known}}


def _freshness_or_none(org: str) -> dict[str, Any] | None:
    try:
        return freshness(org)
    except Exception:  # noqa: BLE001 -- one unreachable organization must not blank the page
        return None
