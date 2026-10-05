"""How big a request may be, and how often the expensive routes may be called.

The body cap is ASGI middleware, so a request over it is refused before any route parses
it, whether it declares a Content-Length or arrives chunked (a chunked body is buffered up
to the cap and replayed; past it, the request is refused).

The rate limits are sliding windows held in this process, like the sign-in limiter
(api/auth/rate_limit.py): with several workers each keeps its own count, so they are a
guard against one account or one leaked embed link keeping the warehouse busy, not a quota.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Depends, HTTPException, Request

from api.auth.config import auth_disabled
from api.auth.dependencies import AuthContext, get_auth_context

MAX_BODY_BYTES = int(os.getenv("PORTAL_MAX_BODY_BYTES", str(2 * 1024 * 1024)))
_TOO_LARGE = json.dumps({"detail": "This request is too large. Send less at once."}).encode()


def _now() -> float:
    return time.monotonic()


class BodySizeLimit:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def _refuse(self, send) -> None:
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(_TOO_LARGE)).encode())]})
        await send({"type": "http.response.body", "body": _TOO_LARGE})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared is not None:
            try:
                too_big = int(declared) > self.max_bytes
            except ValueError:
                too_big = True
            if too_big:
                return await self._refuse(send)
            return await self.app(scope, receive, send)
        # no declared length: read up to the cap, then hand the route exactly what arrived
        messages, size = [], 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] != "http.request":
                break
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                return await self._refuse(send)
            if not message.get("more_body"):
                break
        replay = iter(messages)

        async def replayed():
            return next(replay, None) or await receive()

        return await self.app(scope, replayed, send)


class SlidingWindow:
    def __init__(self, limit: int, seconds: float = 60.0):
        self.limit, self.seconds = limit, seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Count one call; None if allowed, else the seconds until the oldest call leaves the window."""
        now = _now()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                return self.seconds - (now - hits[0])
            hits.append(now)
            return None


_WINDOWS: dict[str, SlidingWindow] = {}


def _by_person(ctx: AuthContext = Depends(get_auth_context)) -> str:
    return ctx.id


def limited(bucket: str, per_minute: int, key: Callable[[Request], str] | None = None):
    """A route dependency: at most `per_minute` calls per person (or per `key(request)` on a
    public route) in any sixty seconds. The auth context is FastAPI's cached one, so a limited
    route signs the caller in once, not twice."""
    window = _WINDOWS.setdefault(bucket, SlidingWindow(per_minute))

    def _check(wait: float | None) -> None:
        if wait is not None:
            seconds = max(1, math.ceil(wait))
            raise HTTPException(status_code=429, headers={"Retry-After": str(seconds)},
                                detail=f"That was asked for faster than the portal allows. Wait {seconds} seconds and try again.")

    if key is not None:
        def limited_by_key(request: Request) -> None:
            _check(window.hit(key(request)))
        return limited_by_key

    def limited_by_person(person: str = Depends(_by_person)) -> None:
        # with sign-in off (development only) every caller is the one dev account, so a
        # per-person window would only throttle the local QA scripts
        if not auth_disabled():
            _check(window.hit(person))
    return limited_by_person


def client_address(request: Request) -> str:
    return request.client.host if request.client else "unknown"
