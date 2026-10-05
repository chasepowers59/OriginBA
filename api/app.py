"""
Unified FastAPI app: NLQ + snapshot explorer (demo database only for explorer).

Run from repo root:
  uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import os
import re
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

# Never under tests: the real .env holds every client's credentials, and once loaded into the
# process every later test could resolve them (2026-10-05: a credential test printed one).
if os.environ.get("ENVIRONMENT") != "test":
    load_dotenv(ROOT / ".env")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.auth import auth_router, init_auth_database
from api.security import is_development
from api.request_tracing import install as install_request_tracing
from api.snapshot_explorer import router as snapshot_router
from api.portal_routes import router as portal_router
from api.data_source_routes import router as data_source_router
from api.database_routes import router as database_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_auth_database()
    from api import cache_warmer
    stop = threading.Event()
    cache_warmer.start(stop)
    yield
    stop.set()


def _docs_urls() -> dict[str, str | None]:
    """The interactive docs and the full schema exist on a development machine only: in
    production they hand anyone a map of every route and parameter (audit 2026-10-05)."""
    from api.security import is_development
    if is_development():
        return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
    return {"docs_url": None, "redoc_url": None, "openapi_url": None}


app = FastAPI(
    title="OriginBA Analytics API",
    description="NLQ and governed snapshot explorer (demo DB only for /snapshots)",
    lifespan=lifespan,
    **_docs_urls(),
)

# scheme://host[:port] -- http and https only, and never a bare "*".
_ORIGIN_RE = re.compile(r"^https?://[A-Za-z0-9.\-]+(?::\d+)?$")


def _cors_origins() -> list[str]:
    from api.security import is_development
    origins = ["https://originba-analytics-portal.vercel.app"]
    if is_development():   # a developer's own UI; never a production origin (audit 2026-10-05)
        origins += ["http://localhost:3000", "http://127.0.0.1:3000"]
    # Audit M9: this list is used with allow_credentials=True. Starlette treats a "*"
    # entry as allow-all, and WITH credentials it echoes the caller's origin instead of
    # sending "*" -- so any website could make credentialed calls carrying a logged-in
    # user's cookies. A wildcard and credentials are mutually exclusive by the CORS
    # spec's own reasoning, so the wildcard is dropped rather than silently honoured.
    # Entries must also look like an origin (scheme://host): a browser Origin header
    # never matches anything else, so a bare hostname only adds noise to the list.
    extra = os.getenv("PORTAL_CORS_ORIGINS", "")
    for origin in extra.split(","):
        origin = origin.strip()
        if not origin or origin in origins:
            continue
        if not _ORIGIN_RE.match(origin):
            continue
        origins.append(origin)
    return origins


# Installed BEFORE CORS: the middleware added last runs outermost, so CORS wraps this one
# and a 500 answered here still carries CORS headers (else the browser shows a CORS error).
install_request_tracing(app)


@app.middleware("http")
async def security_headers(request, call_next):
    """Every API response says what it is and how it may be used. The API serves JSON and
    files, never pages, so nothing in a response may load or frame anything."""
    from api.security import is_development
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
    if not is_development():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # the browser may read the id, so an error on screen can quote its reference, and a
    # letter's font, so its preview can say when the approved face was substituted
    expose_headers=["X-Request-ID", "X-Letter-Font", "X-Letter-Font-Note"],
)

app.include_router(auth_router)
app.include_router(snapshot_router)
app.include_router(portal_router)
app.include_router(data_source_router)
app.include_router(database_router)
from api.dq_routes import router as dq_router
app.include_router(dq_router)
from api.report_schedule_routes import router as report_schedule_router
app.include_router(report_schedule_router)
from api.export_routes import router as export_router
app.include_router(export_router)
from api.embed import router as embed_router
app.include_router(embed_router)
from api.content_pack_routes import router as content_pack_router
app.include_router(content_pack_router)
from api.health_routes import router as health_router
app.include_router(health_router)
from api.ori_routes import router as ori_router
app.include_router(ori_router)
from api.freshness import router as freshness_router
app.include_router(freshness_router)
from api.kpi_alert_routes import router as kpi_alert_router
app.include_router(kpi_alert_router)
from api.annotation_routes import router as annotation_router
app.include_router(annotation_router)
from api.assistant_routes import router as assistant_router
app.include_router(assistant_router)
from api.integrity_routes import router as integrity_router  # noqa: E402
app.include_router(integrity_router)
from api.letters.routes import router as letters_router  # noqa: E402
app.include_router(letters_router)


@app.get("/health")
def health() -> dict:
    # Detail requires PROOF of development, not merely the absence of proof of
    # production: this route takes no auth and the verbose branch names every tenant.
    if not is_development():
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
