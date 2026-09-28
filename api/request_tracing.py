"""A request id, one log line per request, and 500s that name a reference, not a traceback.

X-Request-ID is taken from the caller when it is a short plain token (a proxy's or the
browser's own), otherwise minted. The id is on every response and every log line for the
request, so a user who reports 'Reference: 3f9c...' leads straight to the failure.
"""
from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

log = logging.getLogger("originba.api")
_SANE_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def install(app: FastAPI) -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log.setLevel(logging.INFO)

    @app.middleware("http")
    async def trace(request: Request, call_next):
        given = request.headers.get("X-Request-ID", "")
        rid = given if _SANE_ID.match(given) else uuid.uuid4().hex[:12]
        org = request.headers.get("X-Organization-Id") or "-"
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 -- the one place an unhandled error is caught
            ms = int((time.perf_counter() - started) * 1000)
            log.exception("rid=%s %s %s 500 %dms org=%s", rid, request.method, request.url.path, ms, org)
            response = JSONResponse(status_code=500, content={
                "detail": f"Something went wrong on the server. Reference: {rid}"})
        else:
            ms = int((time.perf_counter() - started) * 1000)
            log.info("rid=%s %s %s %d %dms org=%s", rid, request.method, request.url.path,
                     response.status_code, ms, org)
        response.headers["X-Request-ID"] = rid
        return response
