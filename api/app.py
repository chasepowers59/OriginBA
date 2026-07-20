"""
Unified FastAPI app: NLQ + snapshot explorer (demo database only for explorer).

Run from repo root:
  uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.auth import auth_router, init_auth_database
from api.auth.config import auth_disabled
from api.auth.dependencies import get_auth_context
from api.security import is_production
from api.snapshot_explorer import router as snapshot_router
from api.portal_routes import router as portal_router
from api.data_source_routes import router as data_source_router
from api.database_routes import router as database_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_auth_database()
    yield


app = FastAPI(
    title="OriginBA Analytics API",
    description="NLQ and governed snapshot explorer (demo DB only for /snapshots)",
    lifespan=lifespan,
)

def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://originba-analytics-portal.vercel.app",
    ]
    extra = os.getenv("PORTAL_CORS_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip()
        if origin and origin not in origins:
            origins.append(origin)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(snapshot_router)
app.include_router(portal_router)
app.include_router(data_source_router)
app.include_router(database_router)


def _require_nlq_access(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> None:
    expected = (os.getenv("NLQ_API_KEY") or "").strip()
    if expected and x_api_key and x_api_key.strip() == expected:
        return
    if auth_disabled() and not is_production():
        return
    ctx = get_auth_context(authorization)
    ctx.require_permission("nlq:read")


class NLQRequest(BaseModel):
    query: str


class NLQResponse(BaseModel):
    narrative: str
    acct_id: int | None = None
    metrics: dict | None = None
    resolved_from: str | None = None


def _run_nlq(query: str) -> NLQResponse:
    from pipeline.nlq import run_nlq

    result = run_nlq(query.strip())
    return NLQResponse(
        narrative=result["narrative"],
        acct_id=result.get("acct_id"),
        metrics=result.get("metrics"),
        resolved_from=result.get("resolved_from"),
    )


@app.get("/health")
def health() -> dict:
    if is_production():
        return {"status": "ok"}
    from api.demo_db import demo_configured
    from api.organizations import dev_organization_id, load_organizations

    dev_org = dev_organization_id()
    orgs = load_organizations()
    configured_orgs = [org["id"] for org in orgs if demo_configured(str(org["id"]))]
    return {
        "status": "ok",
        "client": "smartcity",
        "organizations": len(orgs),
        "demo_db_configured": bool(configured_orgs),
        "configured_organizations": configured_orgs,
        "dev_organization": dev_org,
    }


@app.post("/nlq", response_model=NLQResponse)
def nlq_post(req: NLQRequest, _: None = Depends(_require_nlq_access)) -> NLQResponse:
    from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq

    snap = run_snapshot_analytics_nlq(req.query)
    if snap:
        return NLQResponse(
            narrative=snap["narrative"],
            metrics=snap.get("metrics"),
            resolved_from=snap.get("resolved_from"),
        )
    try:
        return _run_nlq(req.query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/nlq", response_model=NLQResponse)
def nlq_get(query: str = "", _: None = Depends(_require_nlq_access)) -> NLQResponse:
    if not query.strip():
        raise HTTPException(status_code=400, detail="Missing query parameter.")
    from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq

    snap = run_snapshot_analytics_nlq(query)
    if snap:
        return NLQResponse(
            narrative=snap["narrative"],
            metrics=snap.get("metrics"),
            resolved_from=snap.get("resolved_from"),
        )
    try:
        return _run_nlq(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
