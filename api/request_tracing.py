"""A request id, one log line per request, and 500s that name a reference, not a traceback.

X-Request-ID is taken from the caller when it is a short plain token (a proxy's or the
browser's own), otherwise minted. The id is on every response and every log line for the
request, so a user who reports 'Reference: 3f9c...' leads straight to the failure.

The same facts are kept in memory for GET /portal/health (api/health_routes.py): requests,
server errors and time per route PATTERN, the slowest recent requests and the last server
errors with their reference. Patterns, never raw paths: an embed link's token is a
credential, so it is masked in the log line too.
"""
from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from api.public_errors import current_reference

log = logging.getLogger("originba.api")
_SANE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_TOKEN_PATH = re.compile(r"^/embed/[^/]+")

SLOW_MS = 2000
KEEP = 50
_lock = threading.Lock()
_started = datetime.now(timezone.utc)
_routes: dict[str, dict[str, int]] = {}
_slow: deque = deque(maxlen=KEEP)
_errors: deque = deque(maxlen=KEEP)


def _route(request: Request) -> str:
    matched = request.scope.get("route")
    return f"{request.method} {getattr(matched, 'path', None) or '(no such route)'}"


def _record(request: Request, rid: str, status: int, ms: int, org: str, error: str | None = None) -> None:
    route = _route(request)
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _lock:
        r = _routes.setdefault(route, {"requests": 0, "server_errors": 0, "total_ms": 0, "max_ms": 0})
        r["requests"] += 1
        r["server_errors"] += status >= 500
        r["total_ms"] += ms
        r["max_ms"] = max(r["max_ms"], ms)
        if ms >= SLOW_MS:
            _slow.appendleft({"reference": rid, "at": when, "route": route, "status": status, "ms": ms, "org": org})
        if status >= 500:
            _errors.appendleft({"reference": rid, "at": when, "route": route, "org": org, "error": error or f"HTTP {status}"})


def snapshot() -> dict:
    with _lock:
        routes = sorted(({"route": k, **v, "avg_ms": v["total_ms"] // max(v["requests"], 1)} for k, v in _routes.items()),
                        key=lambda r: -r["total_ms"])
        return {"started_at": _started.isoformat(timespec="seconds"), "slow_ms": SLOW_MS,
                "requests": sum(r["requests"] for r in routes), "server_errors": sum(r["server_errors"] for r in routes),
                "routes": routes, "slow": list(_slow), "errors": list(_errors)}


def reset() -> None:
    with _lock:
        _routes.clear()
        _slow.clear()
        _errors.clear()


def install(app: FastAPI) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.setLevel(logging.INFO)

    @app.middleware("http")
    async def trace(request: Request, call_next):
        given = request.headers.get("X-Request-ID", "")
        rid = given if _SANE_ID.match(given) else uuid.uuid4().hex[:12]
        current_reference.set(rid)   # api/public_errors.py quotes it in a failure a person sees
        org = request.headers.get("X-Organization-Id") or "-"
        started = time.perf_counter()
        path = _TOKEN_PATH.sub("/embed/<token>", request.url.path)
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 -- the one place an unhandled error is caught
            ms = int((time.perf_counter() - started) * 1000)
            log.exception("rid=%s %s %s 500 %dms org=%s", rid, request.method, path, ms, org)
            _record(request, rid, 500, ms, org, f"{type(exc).__name__}: {str(exc)[:300]}")
            response = JSONResponse(status_code=500, content={
                "detail": f"Something went wrong on the server. Reference: {rid}"})
        else:
            ms = int((time.perf_counter() - started) * 1000)
            log.info("rid=%s %s %s %d %dms org=%s", rid, request.method, path, response.status_code, ms, org)
            _record(request, rid, response.status_code, ms, org)
        response.headers["X-Request-ID"] = rid
        return response
